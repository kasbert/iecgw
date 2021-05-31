
/*
  functions called from iec process
*/

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "arch-config.h"
#include "buffers.h"
#include "iec.h"
#include "debug.h"
#include "errormsg.h"
#include "iecgw.h"

uint8_t command_buffer[CONFIG_COMMAND_BUFFER_SIZE + 2];
uint8_t command_length;

volatile uint8_t led_state;
uint8_t globalflags;
uint16_t datacrc;
uint8_t image_as_dir;
uint8_t rom_filename[ROM_NAME_LENGTH + 1];
uint8_t file_extension_mode;

uint8_t current_device_address;
static int to_iec_read_msg(uint8_t device_address, uint8_t *cmd, uint8_t *secondary, uint8_t *buffer, size_t *size);
static int from_iec_write_msg(uint8_t device_address, uint8_t cmd, uint8_t secondary, uint8_t *buffer, uint8_t size);

// TODO make configurable
uint8_t m_atnPin = 6;
uint8_t m_dataPin = 0;
uint8_t m_clockPin = 1;
uint8_t m_srqInPin = 2;
uint8_t m_resetPin = 5;
uint8_t m_dirtyLedPin = -1;
uint8_t m_busyLedPin = -1;

void gpio_init()
{
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
}

// Called from mainloop system_sleep()
uint8_t check_input() {
  static int counter1 = 0, counter2 = 0;
#ifdef SINGLE_PROCESS
  handle_socket();
#else
  if (common->to_iec_command.cmd != 0) {
    printf("RECEIVED command %d\n", common->to_iec_command.cmd);
    fflush(stdout);
    process_iecgw_msg(common->to_iec_command.device_address, 
      common->to_iec_command.cmd,
      common->to_iec_command.secondary,
      common->to_iec_command.data,
      common->to_iec_command.size
    );
    common->to_iec_command.cmd = 0; // ACK
  }
#endif

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
  switch (cmd)
  {
    case 'x':
      iec_data.bus_state = BUS_SENDATN;
    return ;
  }
}

uint8_t is_hw_address(uint8_t device_address) {
  // Set current address as a side effect
  current_device_address = device_address;
  if (common->socketfds[device_address] < 0) {
    printf("Address %d is not connected1\n", device_address);
    return 0;
  }
  return 1;
}

static int from_iec_write_msg(uint8_t device_address, uint8_t cmd, uint8_t secondary, uint8_t *buffer, uint8_t size)
{
#ifdef SINGLE_PROCESS
  return socket_write_msg(common->socketfds[device_address], cmd, secondary, buffer, size);
#else
  if (common->socketfds[device_address] < 0) {
    printf("Address %d is not connected2\n", device_address);
    return -1;
  }
  // Waith for previous message to be handled
  if (common->from_iec_command.cmd) {
    printf("%lld WAIT SEND\n", timestamp_us()); 
    while (common->from_iec_command.cmd) {
    }
    printf("%lld WAIT SEND ENDn", timestamp_us()); 
  }
  common->from_iec_command.device_address = device_address;
  common->from_iec_command.secondary = secondary;
  common->from_iec_command.size = size;
  memcpy (common->from_iec_command.data, buffer, size);
  common->from_iec_command.cmd = cmd;
  //printf("%lld WAIT SEND ACK\n", timestamp_us()); 
  //while (common->from_iec_command.cmd) {
  //}
  //printf("%lld SEND ACK\n", timestamp_us()); 
  return 0;
#endif
}

static int to_iec_prepare_read_msg(uint8_t device_address) {
#ifdef SINGLE_PROCESS
#else
  if (common->socketfds[device_address] < 0) {
    printf("Address %d is not connected3\n", device_address);
    return -1;
  }
  // TODO there is still a race possibility
  while (common->to_iec_command.cmd) {
    printf("INCOMING!\n");
    check_input();
  }
  // TODO handle device_address
  // common->to_iec_command.device_address = device_address;
#endif
  return 0;
}

static int to_iec_read_msg(uint8_t device_address, uint8_t *cmd, uint8_t *secondary, uint8_t *buffer, size_t *size)
{
  fflush(stdout);
#ifdef SINGLE_PROCESS
  // Blocking read
  return socket_read_msg(common->socketfds[device_address], cmd, secondary, buffer, size);
#else
  if (common->socketfds[device_address] < 0) {
    printf("Address %d is not connected3\n", device_address);
    return -1;
  }
  // common->to_iec_command.device_address = device_address;
  // TODO reconsider device_address
  //printf("%lld WAIT RECEIVE\n", timestamp_us()); 
  while (!common->to_iec_command.cmd) {
    if (!get_atn()) {
      return -1;
    }
  }
  //printf("%lld RECEIVE!\n", timestamp_us()); 
  *cmd = common->to_iec_command.cmd;
  *size = common->to_iec_command.size;
  *secondary = common->to_iec_command.secondary;
  memcpy (buffer, common->to_iec_command.data, *size);
  common->to_iec_command.cmd = 0; // ACK
  return 0;
#endif
}

// Called from iec.c

void parse_doscommand(void)
{
  debug_print_buffer("parse_doscommand", command_buffer, command_length);
  from_iec_write_msg(current_device_address, 'P', 0x0f, command_buffer, command_length);
}

uint8_t load_refill(buffer_t *buf)
{
  uint8_t secondary = buf->secondary;
  uint8_t cmd;
  size_t len = 256;

  printf("%lld load_refill secondary %d\n", timestamp_us(), secondary);

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
    printf("%lld load_refill final %d\n", timestamp_us(), len);
    buf->sendeoi = 1;
    unstick_buffer(buf);
    //buf->read = 0;
    return 0;
  }
  printf("%lld load_refill ok %d\n", timestamp_us(), len);
  return 0;
}

uint8_t save_refill(buffer_t *buf)
{
  uint8_t secondary = buf->secondary;
  printf("%lld save_refill secondary %d [%d]\n", timestamp_us(), secondary, (uint8_t)(buf->position - 2));

  from_iec_write_msg(current_device_address, 'W', secondary, buf->data + 2, buf->position - 2);
  buf->position = 2;
  buf->lastused = -1;
  buf->write = 1;
  buf->mustflush = 0;

  return 0;
}

void file_open(uint8_t secondary)
{
  debug_print_buffer("file_open", command_buffer, command_length);

  buffer_t *buf;

  from_iec_write_msg(current_device_address, 'O', secondary, command_buffer, command_length);

  set_error(ERROR_OK);

  /* If the secondary is already in use, close the existing buffer */
  buf = find_buffer(secondary);
  if (buf != NULL)
  {
    /* FIXME: What should we do if an error occurs? */
    cleanup_and_free_buffer(buf);
  }
  buf = alloc_buffer();
  if (!buf)
    return;

  //uart_trace(command_buffer,0,command_length);
  buf->secondary = secondary;
  buf->lastused = 0;
  buf->sendeoi = 0;
  buf->position = 0;
  if (secondary == 1) {
    // FIXME add support for SEQ write, too    
    buf->read = 0;
    buf->write = 1;
    buf->refill = save_refill;
    buf->position = 2;
    buf->lastused = 255;
    buf->recordlen = 254;
  } else {
    buf->read = 0; // Will be set on load_refill
    buf->write = 0;
    buf->refill = load_refill;
  }
  stick_buffer(buf);

  //remote_refill(buf); // Too slow
}

void file_close(uint8_t secondary)
{
  printf("%lld file_close %d\n", timestamp_us(), secondary);
  from_iec_write_msg(current_device_address, 'C', secondary, 0, 0);
}

void device_hw_address_init() {

}

void uart_putc(char c)
{
  // putchar(c);
}
void uart_putcrlf(void)
{
  // putchar('\n');
}
void uart_puthex(uint8_t num)
{
  // printf("%02x", num);
}

// TODO add leds
void set_dirty_led(uint8_t state) {}
void set_busy_led(uint8_t state) {}
void update_leds(void)
{
  set_busy_led(active_buffers != 0);
  set_dirty_led(get_dirty_buffer_count() != 0);
}

uint8_t jiffy_receive(iec_bus_t *busstate)
{
  printf("jiffy_receive\n");
  return 0;
}

uint8_t jiffy_send(uint8_t value, uint8_t eoi, uint8_t loadflags)
{
  printf("jiffy_send\n");
  return 0;
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
