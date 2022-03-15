#ifndef SOCKET_H
#define SOCKET_H

#include <stdint.h>
#include <stddef.h>

struct iecgw_command {
    uint8_t device_address;
    uint8_t cmd;
    uint8_t secondary;
    size_t size;
    uint8_t data[256];
};

struct iecgw_common {
  int socketfds[32];
  struct iecgw_command to_iec_command;
  struct iecgw_command from_iec_command;
};
extern volatile struct iecgw_common *common;

int iecgw_init();
uint8_t iecgw_loop();

uint8_t handle_socket(long timeout);
uint8_t handle_iecgw();

#endif
