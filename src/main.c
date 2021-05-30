
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
#include "iecgw.h"
#include "debug.h"

uint8_t current_device_address;

static void setup_realtimeish();
void gpio_init();

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
  return iecgw_is_connected(device_address);
}


void parse_doscommand(void)
{
  debug_print_buffer("parse_doscommand", command_buffer, command_length);
  iecgw_write_msg(current_device_address, 'P', 0x0f, command_buffer, command_length);
}

uint8_t load_refill(buffer_t *buf)
{
  uint8_t secondary = buf->secondary;
  printf("%lld load_refill secondary %d\n", timestamp_us(), secondary);

  iecgw_write_msg(current_device_address, 'R', secondary, 0, 0);
  fflush(stdout); // We have time for this

  uint8_t cmd;
  size_t len = 256;

  int l = iecgw_read_msg(current_device_address, &cmd, &secondary, buf->data, &len);
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

  iecgw_write_msg(current_device_address, 'W', secondary, buf->data + 2, buf->position - 2);
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

  iecgw_write_msg(current_device_address, 'O', secondary, command_buffer, command_length);

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
  iecgw_write_msg(current_device_address, 'C', secondary, 0, 0);
}

int main(int argc, char **argv)
{
  char stdout_buffer[4096];
  setup_realtimeish();

  wiringPiSetup();

  signal(SIGPIPE, SIG_IGN);

  // Make stdout buffered, so we may happily use printf
  setvbuf(stdout, stdout_buffer, _IOFBF, sizeof(stdout_buffer));

  if (iecgw_init()) {
    exit(EXIT_FAILURE);
  }

  buffers_init();
  gpio_init();

  iec_init();

  printf("%lld ACCEPTING\n", timestamp_us());
  fflush(stdout);

  iec_mainloop();
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

