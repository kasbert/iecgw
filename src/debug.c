#include <stdio.h>
#include <inttypes.h>

#include "arch-config.h"
#include "debug.h"
#include "iec.h"

void debug_state() {
    printf("%lld STATE %d %-15s %d %-10s ATN %d CLOCK %d DATA %d\n",timestamp_us(),iec_data.bus_state, 
    state2str(iec_data.bus_state), iec_data.device_state, dstate2str(iec_data.device_state),
    get_atn(), get_clock(), get_data());
}

void debug_atn_command(char *message, uint8_t cmd1) {
  printf("%lld %s ATNCMD %02x %-15s dev/sec %d\n", timestamp_us(),message,cmd1,atncmd2str(cmd1),cmd1&0x1f); 
}


char *state2str(int bus_state)
{
  switch (bus_state)
  {
  case BUS_SLEEP:
    return "BUS_SLEEP";
  case BUS_IDLE:
    return "BUS_IDLE";
  case BUS_FOUNDATN:
    return "BUS_FOUNDATN";
  case BUS_ATNACTIVE:
    return "BUS_ATNACTIVE";
  case BUS_FORME:
    return "BUS_FORME";
  case BUS_NOTFORME:
    return "BUS_NOTFORME";
  case BUS_ATNFINISH:
    return "BUS_ATNFINISH";
  case BUS_ATNPROCESS:
    return "BUS_ATNPROCESS";
  case BUS_CLEANUP:
    return "BUS_CLEANUP";
  case BUS_SENDOPEN:
    return "BUS_SENDOPEN";
  case BUS_SENDDATA:
    return "BUS_SENDDATA";
  case BUS_SENDTALK:
    return "BUS_SENDTALK";
  case BUS_SENDCLOSE:
    return "BUS_SENDCLOSE";
  }
  return "UNKNOWN STATE";
}

char *dstate2str(int device_state)
{
  switch (device_state)
  {
  case DEVICE_IDLE:
    return "DEVICE_IDLE";
  case DEVICE_LISTEN:
    return "DEVICE_LISTEN";
  case DEVICE_TALK:
    return "DEVICE_TALK";
  case HOST_ATN:
    return "HOST_ATN";
  case HOST_LISTEN:
    return "HOST_LISTEN";
  case HOST_TALK:
    return "HOST_TALK";
  }
  return "UNKNOWN STATE";
}

char *atncmd2str(int cmd)
{
  if (cmd == 0x3F)
    return "ATN_CODE_UNLISTEN";
  if (cmd == 0x5F)
    return "ATN_CODE_UNTALK";
  switch (cmd & 0xf0)
  {
  case 0x20:
    return "ATN_CODE_LISTEN";
  case 0x40:
    return "ATN_CODE_TALK";
  case 0x60:
    return "ATN_CODE_DATA";
  case 0xE0:
    return "ATN_CODE_CLOSE";
  case 0xF0:
    return "ATN_CODE_OPEN";
  };
  return "UNKNOWN CMD";
}

void debug_print_buffer(const char *msg, unsigned const char *p, size_t size)
{
  printf("%lld %s [%d] '", timestamp_us(), msg, size);
  for (int i = 0; i < size; i++)
  {
    if (p[i] < ' ' || p[i] > 127)
    {
      printf("\\x%02x", p[i]);
    }
    else
    {
      printf("%c", p[i]);
    }
  }
  printf("'\n");
}