#ifndef SOCKET_H
#define SOCKET_H

#include <stdint.h>
#include <stddef.h>

uint8_t iecgw_is_connected(uint8_t device_address);
int iecgw_read_msg(uint8_t device_address, uint8_t *cmd, uint8_t *secondary, uint8_t *buffer, size_t *size);
int iecgw_write_msg(uint8_t device_address, uint8_t cmd, uint8_t secondary, uint8_t *buffer, uint8_t size);

int iecgw_init();

#endif