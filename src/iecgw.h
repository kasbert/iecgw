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

struct {
  int socketfds[32];
#ifndef SINGLE_PROCESS
  struct iecgw_command to_iec_command;
  struct iecgw_command from_iec_command;
#endif
} * common;

int iecgw_init();
uint8_t iecgw_loop();

int socket_write_msg(int fd, uint8_t cmd, uint8_t secondary, uint8_t *buffer, uint8_t size);
int socket_read_msg(int fd, uint8_t *cmd, uint8_t *secondary, uint8_t *buffer, size_t *size);
void process_iecgw_msg(uint8_t device_address, uint8_t cmd, uint8_t secondary, uint8_t *data, size_t len);
uint8_t handle_socket();

#endif