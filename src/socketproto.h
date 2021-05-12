#ifndef SOCKET_H
#define SOCKET_H

#include <stdint.h>
#include <stddef.h>

int socket_available(int fd);
int socket_read(int fd);
int socket_read_buf(int fd, char *buf, size_t len);
int socket_read_msg(int fd, char *c, uint8_t *secondary, uint8_t *buffer, size_t *size);
int socket_write(int fd, char c);
int socket_write_buf(int fd, char *buf, size_t len);
int socket_write_msg(int fd, char c, uint8_t secondary, uint8_t *buffer, uint8_t size);

int socket_init_server();
int socket_accept(int fd);

#endif