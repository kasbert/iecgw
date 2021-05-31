
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <fcntl.h>
#define __USE_GNU
#include <sched.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <signal.h>

#include "arch-config.h"
#include "buffers.h"
#include "iec.h"
#include "iecgw.h"

static void setup_realtimeish();
void gpio_init();

int main(int argc, char **argv)
{
  common = mmap(NULL, sizeof(*common), PROT_READ|PROT_WRITE, MAP_SHARED|MAP_ANONYMOUS, -1, 0);
  memset(common, 0, sizeof (*common));

#ifndef SINGLE_PROCESS
  switch (fork()) {
    default: // Parent, socket process
#endif
      signal(SIGPIPE, SIG_IGN);
      // TODO wait child death

      if (iecgw_init()) {
        exit(EXIT_FAILURE);
      }
#ifndef SINGLE_PROCESS
      iecgw_loop();
      break;

    case 0: // Child, IEC process
#endif
    {
      char stdout_buffer[8192];
      // Make stdout buffered, so we may happily use printf
      setvbuf(stdout, stdout_buffer, _IOFBF, sizeof(stdout_buffer));
      setup_realtimeish();

      wiringPiSetup();

      buffers_init();
      gpio_init();

      iec_init();
      iec_mainloop();
    }
#ifndef SINGLE_PROCESS
    break;

    case -1: // erorr
      perror("fork");
      break;

  }
#endif
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

