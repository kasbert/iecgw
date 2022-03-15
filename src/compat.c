
/*
  functions called from iec process
*/

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <sys/stat.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/select.h>

#include "arch-config.h"
#include "iec.h"
#include "debug.h"
#include "iecgw.h"
#include "buffers.h"
#include "errormsg.h"


volatile uint8_t led_state;
uint8_t globalflags;
uint16_t datacrc;
uint8_t image_as_dir;
uint8_t rom_filename[ROM_NAME_LENGTH + 1];
uint8_t file_extension_mode;

uint8_t current_device_address;
static int to_iec_read_msg(uint8_t device_address, uint8_t *cmd, uint8_t *secondary, uint8_t *buffer, size_t *size);
int from_iec_write_msg(uint8_t device_address, uint8_t cmd, uint8_t secondary, uint8_t *buffer, uint8_t size);
void process_iecgw_msg(uint8_t device_address, uint8_t cmd, uint8_t secondary, uint8_t *data, size_t len);

// TODO make configurable
#ifdef WIRINGPI
uint8_t m_atnPin = 6;
uint8_t m_dataPin = 0;
uint8_t m_clockPin = 1;
uint8_t m_srqInPin = 2;
uint8_t m_resetPin = 5;

#else
uint8_t m_atnPin = SUNXI_GPA(7);
uint8_t m_dataPin = SUNXI_GPA(12);
uint8_t m_clockPin = SUNXI_GPA(11);
uint8_t m_srqInPin = SUNXI_GPA(6);
uint8_t m_resetPin = SUNXI_GPA(1);

struct gpio_reg gpio_reg_atn;
struct gpio_reg gpio_reg_data;
struct gpio_reg gpio_reg_clock;
struct gpio_reg gpio_reg_srq_in;
struct gpio_reg gpio_reg_reset;

static uint64_t epochMicro ;

unsigned int micros (void)
{
  uint64_t now ;
  struct  timespec ts ;

  // Does not trigger a system call, just a read from memory
  clock_gettime (CLOCK_MONOTONIC_RAW, &ts) ;
  now  = (uint64_t)ts.tv_sec * (uint64_t)1000000 + (uint64_t)(ts.tv_nsec / 1000) ;

  return (uint32_t)(now - epochMicro) ;
}
#endif

uint8_t m_dirtyLedPin = -1;
uint8_t m_busyLedPin = -1;

int gpio_init()
{
#ifdef WIRINGPI
  wiringPiSetup();

  pinMode(m_atnPin, INPUT);
  pinMode(m_dataPin, INPUT);
  pinMode(m_clockPin, INPUT);
  pinMode(m_srqInPin, INPUT);
  pinMode(m_resetPin, INPUT);

  pullUpDnControl(m_atnPin, PUD_UP);
  pullUpDnControl(m_dataPin, PUD_UP);
  pullUpDnControl(m_clockPin, PUD_UP);
  pullUpDnControl(m_srqInPin, PUD_UP);
  pullUpDnControl(m_resetPin, PUD_UP);

#else
  struct timespec ts ;
  clock_gettime (CLOCK_MONOTONIC_RAW, &ts) ;
  epochMicro = (uint64_t)ts.tv_sec * (uint64_t)1000000 + (uint64_t)(ts.tv_nsec /    1000L) ;

  if (SETUP_OK != sunxi_gpio_init()) {
      return (-1);
  }
  gpio_reg_init(&gpio_reg_atn, m_atnPin);
  gpio_reg_init(&gpio_reg_data, m_dataPin);
  gpio_reg_init(&gpio_reg_clock, m_clockPin);
  gpio_reg_init(&gpio_reg_srq_in, m_srqInPin);
  gpio_reg_init(&gpio_reg_reset, m_resetPin);
  gpio_reg_set_cfg(&gpio_reg_atn, SUNXI_GPIO_INPUT);
  gpio_reg_set_cfg(&gpio_reg_data, SUNXI_GPIO_INPUT);
  gpio_reg_set_cfg(&gpio_reg_clock, SUNXI_GPIO_INPUT);
  gpio_reg_set_cfg(&gpio_reg_srq_in, SUNXI_GPIO_INPUT);
  gpio_reg_set_cfg(&gpio_reg_reset, SUNXI_GPIO_INPUT);
  gpio_reg_set_pull(&gpio_reg_atn, UP);
  gpio_reg_set_pull(&gpio_reg_data, UP);
  gpio_reg_set_pull(&gpio_reg_clock, UP);
  gpio_reg_set_pull(&gpio_reg_srq_in, UP);
  gpio_reg_set_pull(&gpio_reg_reset, UP);
#endif
  return 0;
}

volatile uint32_t *tmrs;

volatile uint32_t *timer_register;

#define TMR_IO_BASE 0x01c20c00

int sunxi_tmrs_init(void) {
    int fd;
    unsigned int addr_start, addr_offset;
    unsigned int PageSize, PageMask;
    long int *gpio_map = NULL;


    fd = open("/dev/mem", O_RDWR);
    if(fd < 0) {
        return SETUP_DEVMEM_FAIL;
    }

    PageSize = sysconf(_SC_PAGESIZE);
    PageMask = (~(PageSize-1));

    addr_start = TMR_IO_BASE & PageMask;
    addr_offset = TMR_IO_BASE & ~PageMask;

    gpio_map = (void *)mmap(0, PageSize*2, PROT_READ|PROT_WRITE, MAP_SHARED, fd, addr_start);
    if(gpio_map == MAP_FAILED) {
        return SETUP_MMAP_FAIL;
    }
    close(fd);

    tmrs = (uint32_t*)((unsigned int)gpio_map + addr_offset);

    // TODO check if tmrs[8] == 5
    timer_register = tmrs + 10;

    return SETUP_OK;
}


void debug_show_buffer(buffer_t *buf, char *message) {
  printf("%lld %s buffer sec %d %s%s%s%s%s %d-%d %d\n", timestamp_us(), message, buf->secondary,
  buf->write?"Write":"", buf->read?"Read":"", buf->sticky?"Sticky":"", buf->dirty?"Dirty":"", buf->sendeoi?"Sendeoi":""
  , buf->position, buf->lastused, buf->recordlen);
}

// Called from mainloop system_sleep()
uint8_t check_input() {
  static int counter1 = 0, counter2 = 0;
#ifdef SINGLE_PROCESS
  handle_socket(0);
  fflush(stdout);
#endif
  if (common->to_iec_command.cmd != 0) {
    printf("%lld RECEIVED socket command %c\n", timestamp_us(), common->to_iec_command.cmd);
    fflush(stdout);
    process_iecgw_msg(common->to_iec_command.device_address,
      common->to_iec_command.cmd,
      common->to_iec_command.secondary,
      (uint8_t*)common->to_iec_command.data,
      common->to_iec_command.size
    );
    common->to_iec_command.cmd = 0; // ACK
  }

  if (counter1 == 0) {
      fflush(stdout);
  }

  if (counter1++ == 1000000)
  {
    putchar((counter2 % 40 >= 20) ? '+' : '-');
    if (counter2 % 20 == 19)
    {
      putchar('\r');
    }
    ++counter2;
    counter2 = counter2 % 40;
    counter1 = 0;
  }

  return 0;
}

void process_iecgw_msg(uint8_t device_address, uint8_t cmd, uint8_t secondary, uint8_t *data, size_t len) {
  uint8_t ieccmd = secondary;
  switch (cmd)
  {
    case 'o':
      iec_data.bus_state = BUS_SENDOPEN;
      ieccmd = 0xf0 + secondary;
      break;
    case 'd':
      iec_data.bus_state = BUS_SENDDATA;
      ieccmd = 0x60 + secondary;
      break;
    case 't':
      iec_data.bus_state = BUS_SENDTALK;
      break;
    case 'c':
      iec_data.bus_state = BUS_SENDCLOSE;
      ieccmd = 0xe0 + secondary;
      break;
  }
  iec_data.device_address = 8; // FIXME secondary >> 4;
  iec_data.secondary_address = secondary & 0xf;
  if (len > 0) {
    buffer_t *buf = alloc_buffer();
    if (!buf) {
      printf("Cannot allocate buffer\n");
      iec_data.bus_state = BUS_CLEANUP;
      return; // FIXME
    }
    buf->secondary = secondary;
    buf->pvt.sockcmd.cmd = ieccmd;

    buf->read = 1;
    buf->write = 0;
    buf->refill = 0 ; //FIXME
    memcpy(buf->data, data, len);
    buf->lastused = len - 1;
    buf->position = 0;
    buf->sendeoi = 1;
    debug_show_buffer(buf, "host");
  }
}

uint8_t is_hw_address(uint8_t device_address) {
  // Set current address as a side effect
  current_device_address = device_address;
  if (common->socketfds[device_address] < 0) {
    return 0;
  }
  return 1;
}

int from_iec_write_msg(uint8_t device_address, uint8_t cmd, uint8_t secondary, uint8_t *buffer, uint8_t size)
{
  if (common->socketfds[device_address] < 0) {
    printf("from_iec_write_msg: address %d is not connected2\n", device_address);
    return -1;
  }
  // Wait for previous message to be handled
  if (common->from_iec_command.cmd) {
    // Good place for deadlock
    printf("%lld WAIT SEND\n", timestamp_us()); 
    while (common->from_iec_command.cmd) {
    }
    printf("%lld WAIT SEND END\n", timestamp_us()); 
  }
  common->from_iec_command.device_address = device_address;
  common->from_iec_command.secondary = secondary;
  common->from_iec_command.size = size;
  memcpy ((void*)common->from_iec_command.data, buffer, size);
  common->from_iec_command.cmd = cmd;
  //printf("%lld WAIT SEND ACK\n", timestamp_us()); 
  //while (common->from_iec_command.cmd) {
  //}
  //printf("%lld SEND ACK\n", timestamp_us()); 
#ifndef SINGLE_PROCESS
  return 0;
#else
  return handle_iecgw();
#endif
}

static int to_iec_prepare_read_msg(uint8_t device_address) {
  if (common->socketfds[device_address] < 0) {
    printf("to_iec_prepare_read_msg: address %d is not connected3\n", device_address);
    return -1;
  }
#ifndef SINGLE_PROCESS
  // TODO there is still a race possibility
  while (common->to_iec_command.cmd) {
    printf("INCOMING!\n");
    check_input();
  }
#endif
  // TODO handle device_address
  // common->to_iec_command.device_address = device_address;
  return 0;
}

static int to_iec_read_msg(uint8_t device_address, uint8_t *cmd, uint8_t *secondary, uint8_t *buffer, size_t *size)
{
  fflush(stdout);
  if (common->socketfds[device_address] < 0) {
    printf("Address %d is not connected3\n", device_address);
    return -1;
  }
  // common->to_iec_command.device_address = device_address;
  // TODO reconsider device_address
  //printf("%lld WAIT RECEIVE\n", timestamp_us()); 
  while (!common->to_iec_command.cmd) {
#ifdef SINGLE_PROCESS
    handle_socket(0);
#endif
    if (!get_atn()) {
      return -1;
    }
  }
  //printf("%lld RECEIVE!\n", timestamp_us()); 
  *cmd = common->to_iec_command.cmd;
  *size = common->to_iec_command.size;
  *secondary = common->to_iec_command.secondary;
  memcpy (buffer, (void*)common->to_iec_command.data, *size);
  common->to_iec_command.cmd = 0; // ACK
  return 0;
}

// Called from iec.c

void parse_doscommand(void)
{
  printf("%lld parse_doscommand sec\n", timestamp_us());
  //debug_print_buffer("parse_doscommand", command_buffer, command_length);
}

void file_open(uint8_t secondary)
{
  /* Don't do any slow operations here. We are still in ATN handling. A talk or listen will follow */
  printf("%lld file_open sec %d\n", timestamp_us(), secondary);
  //debug_print_buffer("file_open", command_buffer, command_length);
}


uint8_t load_refill(buffer_t *buf)
{
  uint8_t secondary = buf->secondary;
  uint8_t cmd;
  size_t len = 256;

  //printf("%lld load_refill secondary %d\n", timestamp_us(), secondary);

  to_iec_prepare_read_msg(current_device_address);
  from_iec_write_msg(current_device_address, 'R', secondary, 0, 0);
  fflush(stdout); // We have time for this

  int l = to_iec_read_msg(current_device_address, &cmd, &secondary, buf->data, &len);
  if (l < 0)
  {
    set_error(ERROR_IMAGE_INVALID);
    return -1;
  }
  if (cmd == ':')
  {
    set_error(buf->data[0]);
    return -1;
  }
  if (cmd != 'E' && cmd != 'B')
  {
    printf("%lld load_refill protocol error %d\n", timestamp_us(), cmd);
    set_error(ERROR_IMAGE_INVALID);
    return -1;
  }

  buf->position = 0;
  buf->lastused = len - 1;
  buf->read = 1;
  if (cmd == 'E')
  {
    buf->sendeoi = 1;
    unstick_buffer(buf);
    //buf->read = 0;
  }
  debug_show_buffer(buf, "load_refill ok");
 extern int errors;
  if (errors) {
    printf("jiffy errors %d\n", errors);
  debug_state();
    errors = 0;
  }
  return 0;
}

uint8_t save_refill(buffer_t *buf)
{
  uint8_t secondary = buf->secondary;
  uint8_t cmd2 = 'P';
  uint8_t cmd = buf->pvt.sockcmd.cmd;

  debug_show_buffer(buf, "save_refill");
  //printf("%lld save_refill cmd %02x secondary %d\n", timestamp_us(), cmd, secondary);
  if ((cmd & 0xf0) == 0xf0) { // OPEN
    cmd2 = 'O';
    debug_print_buffer("save_refill open", buf->data + 2,  buf->lastused - 1);
  } else if ((cmd & 0xf0) == 0x60) { // DATA
    cmd2 = 'W';
  } 

  from_iec_write_msg(current_device_address, cmd2, secondary, buf->data + 2, buf->lastused - 1);
  buf->position = 2; // Use only 254 bytes in buffer
  buf->lastused = 1;
  buf->write = 1;
  buf->mustflush = 0;
  mark_buffer_clean(buf);

  return 0;
}

void file_close(uint8_t secondary)
{
  buffer_t *buf;
  printf("%lld file_close %d\n", timestamp_us(), secondary);
  buf = find_buffer(secondary);
  if (buf != NULL) {
    // TODO should we refill it, if writing ?
    debug_show_buffer(buf, "file_close");
    unstick_buffer(buf);
    free_buffer(buf);
  }
  from_iec_write_msg(current_device_address, 'C', secondary, 0, 0);
}

void device_hw_address_init() {

}

void uart_putc(char c)
{
  //putchar(c);
}
void uart_putcrlf(void)
{
  //putchar('\n');
}
void uart_puthex(uint8_t num)
{
  //printf("%02x", num);
}

// TODO add leds
void set_dirty_led(uint8_t state) {}
void set_busy_led(uint8_t state) {}
void update_leds(void)
{
  //set_busy_led(active_buffers != 0);
  //set_dirty_led(get_dirty_buffer_count() != 0);
}

int16_t dolphin_getc(void)
{
  printf("dolphin_getc\n");
  return 0;
}

uint8_t dolphin_putc(uint8_t data, uint8_t with_eoi)
{
  printf("dolphin_putc\n");
  return 0;
}
