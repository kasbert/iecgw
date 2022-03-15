
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <fcntl.h>
#define __USE_GNU
#include <sched.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <signal.h>

#include "arch-config.h"
#include "buffers.h"
#include "iec.h"
#include "iecgw.h"

static void setup_realtimeish();
int gpio_init();
int sunxi_tmrs_init(void);
void proc_exit()
{
  exit(0);
}

volatile struct iecgw_common *common;


int main(int argc, char **argv)
{
  common = mmap(NULL, sizeof(*common), PROT_READ|PROT_WRITE, MAP_SHARED|MAP_ANONYMOUS, -1, 0);
  memset((void *)common, 0, sizeof (*common));

#ifndef SINGLE_PROCESS
  switch (fork()) {
    case 0: // Child, socket process
    if (prctl(PR_SET_PDEATHSIG, SIGTERM) == -1) {
      perror("prctl");
      exit(EXIT_FAILURE);
    }
#endif
      signal(SIGPIPE, SIG_IGN);

      if (iecgw_init()) {
        exit(EXIT_FAILURE);
      }
#ifndef SINGLE_PROCESS
      setuid(65534); // nobody in my system
      iecgw_loop();
      break;

    default: // Parent, IEC process
  		signal (SIGCHLD, proc_exit);
      // TODO wait child death
#endif
    {
      char stdout_buffer[8192];
      // Make stdout buffered, so we may happily use printf
      setvbuf(stdout, stdout_buffer, _IOFBF, sizeof(stdout_buffer));
      setup_realtimeish();

      buffers_init();
      if (gpio_init()) {
          printf("Error - Failed to initialize GPIO\n");
          exit(EXIT_FAILURE);
      }
      sunxi_tmrs_init();
      iec_init();
      setuid(65534); // nobody in my system
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
  char *p = strstr(buf, "isolcpus=nohz,domain,1");
  if (!p)
  {
    puts(buf);
    puts("Add isolcpus=nohz,domain,1 nohz_full=1 rcu_nocbs=1 to kernel boot options");
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

  // YOU MUST have NOHZ_FULL kernel compile option set
  /*
  gzip -d < /proc/config.gz | grep NO_HZ
  CONFIG_NO_HZ_COMMON=y
  CONFIG_NO_HZ_IDLE=y
  CONFIG_NO_HZ_FULL=y
  CONFIG_NO_HZ=y
  */
  // IF your kernel does not have it, you must recompile the kernel with the option


  // echo performance | sudo tee /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
  // find /sys/devices/virtual/workqueue -name cpumask  -exec sh -c 'echo 1 > {}' ';'
  // apt install linux-perf
  // extraargs=isolcpus=1 nohz_full=1 rcu_nocbs=1
  // sysctl vm.stat_interval=120
  // apt install irqbalance
  // irqbalance --foreground --oneshot
  // taskset -c 0-3 /home/kasper/hiccups/build/hiccups | column -t -c 1,2,3,4,5,6
  // cat /proc/interrupts
}

