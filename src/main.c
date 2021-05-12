
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#define __USE_GNU
#include <sched.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <signal.h>

#include "arch-config.h"
#include "buffers.h"
#include "iec.h"
#include "errormsg.h"
#include "socketproto.h"
#include "debug.h"

uint8_t command_buffer[CONFIG_COMMAND_BUFFER_SIZE + 2];
uint8_t command_length;

volatile uint8_t led_state;
uint8_t globalflags;
uint16_t datacrc;
uint8_t image_as_dir;
uint8_t rom_filename[ROM_NAME_LENGTH + 1];
uint8_t file_extension_mode;

// TODO make configurable
uint8_t m_atnPin = 6;
uint8_t m_dataPin = 0;
uint8_t m_clockPin = 1;
uint8_t m_srqInPin = 2;
uint8_t m_resetPin = 5;
uint8_t m_dirtyLedPin = -1;
uint8_t m_busyLedPin = -1;

// FIXME allow multiple devices
static int sockfd;
static int inFd = 0;
static int outFd = 1;
static uint8_t device_address = 8;

static void setup_realtimeish();
static void gpio_init();

uint8_t device_hw_address()
{
  return device_address;
}
void device_hw_address_init()
{
}

void parse_doscommand(void)
{
  debugPrint("parse_doscommand", command_buffer, command_length);
  socket_write_msg(outFd, 'P', 0x0f, command_buffer, command_length);
}

uint8_t load_refill(buffer_t *buf)
{
  uint8_t secondary = buf->secondary;
  printf("%lld load_refill secondary %d\n", timestamp_us(), secondary);

  socket_write_msg(outFd, 'R', secondary, 0, 0);
  fflush(stdout); // We have time for this

  char cmd;
  size_t len = 256;

  int l = socket_read_msg(inFd, &cmd, &secondary, buf->data, &len);
  if (l < 0)
  {
    set_error(ERROR_IMAGE_INVALID);
    return -1;
  }
  if (cmd == ':')
  {
    set_error(len);
    return -1;
  }
  if (cmd != 'E' && cmd != 'B')
  {
    printf("%lld load_refill protocol error %d\n", timestamp_us(), cmd);
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

  socket_write_msg(outFd, 'W', secondary, buf->data + 2, buf->position - 2);
  buf->position = 2;
  buf->lastused = -1;
  buf->write = 1;
  buf->mustflush = 0;

  fflush(stdout); // We have time for this
  return 0;
}

void file_open(uint8_t secondary)
{
  debugPrint("file_open", command_buffer, command_length);

  buffer_t *buf;
  uint8_t i = 0;

  socket_write_msg(outFd, 'O', secondary, command_buffer, command_length);

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
  socket_write_msg(outFd, 'C', secondary, 0, 0);
}

static int counter1 = 0, counter2 = 0;

uint8_t socket_loop()
{
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
    fflush(stdout);
    counter2 = ++counter2 % 40;
    counter1 = 0;
  }

  if (counter1 % 10000 == 0)
  while (socket_available(inFd))
  {
    char cmd;
    uint8_t secondary, data[256];
    size_t len = 256;
    /*
    // FIXME blocking read
    int l = socket_read_msg(inFd, &cmd, &secondary, data, &len);
    if (l == -1)
    {
      return 0;
    }
    data[len] = 0;
    printf("GOT %d %d [%d]\n", cmd, secondary, len);
    debugPrint("socket_loop", data, len);
    // TODO
    switch (cmd)
    {
      case 'x':
      break;
    }
    */

    /*
    */
    int c = socket_read(inFd);
    if (c == -1)
    {
      return 0;
    }
    printf("Got extra char %d\n", c);
  }
  return 1;
}

int main(int argc, char **argv)
{
  char stdout_buffer[4096];
  setup_realtimeish();

  wiringPiSetup();

  signal(SIGPIPE, SIG_IGN);

  // Make stdout buffered, so we may happily use printf
  setbuf(stdout, stdout_buffer);

  sockfd = socket_init_server();

  buffers_init();
  gpio_init();

  iec_init();

  while (1)
  {

    printf("%lld ACCEPTING\n", timestamp_us());
    /* Accept actual connection from the client */
    int newsockfd = socket_accept(sockfd);

    if (newsockfd < 0)
    {
      perror("accept");
      exit(1);
    }
    printf("%lld ACCEPTED\n", timestamp_us());

    inFd = outFd = newsockfd;

    char const *str = "iecgw server";
    int n = socket_write_msg(outFd, 'I', 0, (uint8_t *)str, strlen(str));
    if (n < 0)
    {
      perror("ERROR writing to socket");
      exit(1);
    }

    char buffer[256];
    uint8_t secondary;
    char cmd;
    size_t len = 256;
    int l = socket_read_msg(inFd, &cmd, &secondary, buffer, &len);
    if (l < 0 || cmd != 'I' || secondary > 15)
    {
      // Go away. Didn't know the magic word
      printf("%lld protocol error\n", timestamp_us());
      close(inFd);
      continue;
    }
    device_address = secondary;
    printf("%lld DEVICE %d\n", timestamp_us(), (int)device_address);

    iec_mainloop();

    printf("%lld DISCONNECTED\n", timestamp_us());
  }
}

void setup_realtimeish()
{
  char buf[1024];

  int fd = open("/proc/cmdline", O_RDONLY);
  if (fd < 0)
  {
    perror("Cannot open /proc/cmdline");
    exit(EXIT_FAILURE);
  }
  int len = read(fd, buf, sizeof(buf) - 1);
  if (len <= 0)
  {
    perror("Cannot read /proc/cmdline");
    exit(EXIT_FAILURE);
  }
  buf[len] = 0;
  char *p = strstr(buf, "isolcpus=1");
  if (!p)
  {
    puts(buf);
    puts("Add isolcpu=1 to kernel boot options");
    exit(EXIT_FAILURE);
  }

  // Assign core 1 for this process
  cpu_set_t cpuset;
  CPU_ZERO(&cpuset);
  CPU_SET(1, &cpuset);
  if (sched_setaffinity(getpid(), sizeof(cpu_set_t), &cpuset))
  {
    perror("Cannot sched_setaffinity");
    exit(EXIT_FAILURE);
  }

  if (mlockall(MCL_CURRENT | MCL_FUTURE))
  {
    perror("Cannot mlockall");
    exit(EXIT_FAILURE);
  }

  /*
  struct sched_param param;
   int pid_num = 0;

   param.sched_priority = 99;
   sched_setscheduler(pid_num, SCHED_FIFO, &param);
   */

  // echo performance | sudo tee /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
  // find /sys/devices/virtual/workqueue -name cpumask  -exec sh -c 'echo 1 > {}' ';'
  // apt install linux-perf
  // extraargs=isolcpus=1 nohz_full=1 rcu_nocbs=1
  // sysctl vm.stat_interval=120
  // apt install irqbalance
  // irqbalance --foreground --oneshot
  // taskset -c 0-3 /home/kasper/hiccups/build/hiccups | column -t -c 1,2,3,4,5,6
}

void gpio_init()
{
  pinMode(m_atnPin, INPUT);
  pinMode(m_dataPin, INPUT);
  pinMode(m_clockPin, INPUT);
  pinMode(m_srqInPin, INPUT);
  pinMode(m_resetPin, INPUT);
}

void uart_putc(char c)
{
  putchar(c);
}
void uart_putcrlf(unsigned int i)
{
  putchar('\n');
}
void uart_puthex(uint8_t num)
{
  printf("%02x", num);
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
}

uint8_t jiffy_send(uint8_t value, uint8_t eoi, uint8_t loadflags)
{
  printf("jiffy_send\n");
}

int16_t dolphin_getc(void)
{
  printf("dolphin_getc\n");
}

uint8_t dolphin_putc(uint8_t data, uint8_t with_eoi)
{
  printf("dolphin_putc\n");
}
