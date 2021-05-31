/*
 * Socket server
*/

#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <fcntl.h>
#include <sys/select.h>
#include <sys/ioctl.h>
#include <netdb.h>
#include <netinet/in.h>

#include "iecgw.h"
#include "debug.h"
#include "arch-config.h"

//static int socket_write(int fd, char c);
static int socket_write_buf(int fd, uint8_t *buf, size_t len);
//static int socket_available(int fd);
//static int socket_read(int fd);
//static int socket_read_buf(int fd, uint8_t *buf, size_t len);
static int socket_accept(int fd);

static int serverfd;

void doflush() {
  fflush(stdout);
}

#ifndef SINGLE_PROCESS
static int to_iec_write_msg(uint8_t device_address, uint8_t cmd, uint8_t secondary, uint8_t *buffer, uint8_t size)
{
  // Waith for previous message to be handled
  if (common->to_iec_command.cmd) {
    printf("%lld* SEND IEC WAIT\n", timestamp_us());
    while (common->to_iec_command.cmd) {
    }
    printf("%lld* SEND IEC WAIT END\n", timestamp_us());
  }
  common->to_iec_command.device_address = device_address;
  common->to_iec_command.secondary = secondary;
  common->to_iec_command.size = size;
  memcpy (common->to_iec_command.data, buffer, size);
  common->to_iec_command.cmd = cmd;
  //printf("%lld* SEND IEC WAIT\n", timestamp_us());
  //while (common->to_iec_command.cmd) {
  //}
  //printf("%lld* SEND IEC WAIT END\n", timestamp_us());
  return 0;
}

uint8_t iecgw_loop()
{
  printf("%lld* ACCEPTING\n", timestamp_us());
  while (1) {
    // Receive message from IEC
    if (common->from_iec_command.cmd) {
      uint8_t device_address = common->from_iec_command.device_address;
      if (common->socketfds[device_address] < 0) {
        printf("%lld* Address %d is not connected3\n", timestamp_us(), device_address);
      } else {
        socket_write_msg(common->socketfds[device_address], 
        common->from_iec_command.cmd, 
        common->from_iec_command.secondary, 
        common->from_iec_command.data, 
        common->from_iec_command.size);
      }
      common->from_iec_command.cmd = 0; // ACK
    }

    handle_socket();
  }
}
#endif

uint8_t handle_socket() {
  fd_set rfds;
  struct timeval tv = {0, 100};
  int retval;
  int maxfd = serverfd;
  FD_ZERO(&rfds);
  FD_SET(serverfd, &rfds);
  for (int i = 0; i < 32; i++) {
    if (common->socketfds[i] >= 0) {
      FD_SET(common->socketfds[i], &rfds);
      if (common->socketfds[i] > maxfd) {
        maxfd = common->socketfds[i];
      }
    }
  }
  retval = select(maxfd + 1, &rfds, NULL, NULL, &tv);
  if (retval == -1)
  {
    perror("socket_available");
    return 0;
  }
  if (FD_ISSET(serverfd, &rfds)) {
    /* Accept actual connection from the client */
    socket_accept(serverfd);
  }
  for (int i = 0; i < 32; i++) {
    if (common->socketfds[i] >= 0 && FD_ISSET(common->socketfds[i], &rfds)) {
      uint8_t cmd;
      uint8_t secondary, data[256];
      size_t len = 256;
      // TODO remove blocking read
      // printf("%lld* READING %d\n", timestamp_us(), i);
      int l = socket_read_msg(common->socketfds[i], &cmd, &secondary, data, &len);
      if (l == -1)
      {
        close(common->socketfds[i]);
        common->socketfds[i] = -1;
        printf("%lld* DISCONNECTED\n", timestamp_us());
        return 1;
      }
      data[len] = 0;
      printf("%lld* SOCKET RECV cmd:%d sec:%d [%d]\n", timestamp_us(), cmd, secondary, len);
      //debug_print_buffer("iecgw_loop", data, len);
#ifdef SINGLE_PROCESS
      process_iecgw_msg(i, cmd, secondary, data, len);
#else
      to_iec_write_msg(i, cmd, secondary, data, len);
#endif
    }
  }
  return 0;
}

/*-
int socket_available(int fd)
{
  fd_set rfds;
  struct timeval tv = {0, 0};
  int retval;
  FD_ZERO(&rfds);
  FD_SET(fd, &rfds);
  retval = select(fd + 1, &rfds, NULL, NULL, &tv);
  if (retval == -1)
  {
    perror("socket_available");
    return 0;
  }
  return FD_ISSET(fd, &rfds);
}
*/

int socket_read_msg(int fd, uint8_t *cmd, uint8_t *secondary, uint8_t *buffer, size_t *size)
{
  ssize_t l = read(fd, cmd, 1);
  if (l < 1) goto errorout;
  l = read(fd, secondary, 1);
  if (l < 1) goto errorout;

  uint8_t len;
  l = read(fd, &len, 1);
  if (l < 1) goto errorout;
  if (!len) {
    return 1;
  }
  if (size && len > *size) len = *size;

  size_t total = 0;
  while (total < len) {
    l = read(fd, buffer + total, len - total);
    if (l < 1) goto errorout;
    total += l;
  }
  if (size) *size = len;
  return 1;

  errorout:
    perror("socket_read_msg");
    return -1;
}

/*
int socket_read(int fd)
{
  char buf[1];
  ssize_t l = read(fd, buf, 1);
  if (l < 1)
  {
    perror("socket_read");
    return -1;
  }
  return buf[0];
}

int socket_read_buf(int fd, uint8_t *buf, size_t len)
{
  size_t total = 0;
  while (total < len) {
    ssize_t l = read(fd, buf + total, len - total);
    if (l < 1)
    {
      perror("socket_read_buf");
      return -1;
    }
    total += l;
  }
  return len;
}
*/

int socket_write_msg(int fd, uint8_t cmd, uint8_t secondary, uint8_t *buffer, uint8_t size)
{
  ssize_t l = write(fd, &cmd, 1);
  if (l < 1) goto errorout;
  l = write(fd, &secondary, 1);
  if (l < 1) goto errorout;
  l = write(fd, &size, 1);
  if (l < 1) goto errorout;
  return buffer ? socket_write_buf(fd, buffer, size) : 3;
  errorout:
    perror("socket_write_msg");
    return -1;
}

/*-
int socket_write(int fd, char c)
{
  ssize_t l = write(fd, &c, 1);
  if (l < 1)
  {
    perror("socket_write");
    return -1;
  }
  return 1;
}
*/

int socket_write_buf(int fd, uint8_t *buf, size_t len)
{
  size_t total = 0;
  while (total < len) {
    ssize_t l = write(fd, buf + total, len - total);
    if (l < 1)
    {
      perror("socket_write_buf");
      return -1;
    }
    total += l;
  }
  return len;
}

int iecgw_init()
{
  int portno;
  struct sockaddr_in serv_addr;

  for (int i = 0; i < 32; i++) {
      common->socketfds[i] = -1;
  }

  int sockfd = socket(AF_INET, SOCK_STREAM, 0);

  if (sockfd < 0)
  {
    perror("iecgw_init server socket");
    return -1;
  }

  int enable = 1;
  if (setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &enable, sizeof(int)) < 0)
    perror("setsockopt(SO_REUSEADDR) failed");
  memset((char *)&serv_addr, 0, sizeof(serv_addr));
  portno = 1541;

  serv_addr.sin_family = AF_INET;
  serv_addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
  serv_addr.sin_port = htons(portno);

  if (bind(sockfd, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0)
  {
    perror("iecgw_init socket bind");
    return -1;
  }

  listen(sockfd, 1);
  serverfd = sockfd;
  return 0;
}

static int socket_accept(int fd) {
    struct sockaddr_in cli_addr;
    socklen_t clilen = sizeof(cli_addr);
    int newsockfd = accept(fd, (struct sockaddr *)&cli_addr, &clilen);

    if (newsockfd < 0)
    {
      perror("accept");
      return 1;
    }
    printf("%lld* ACCEPTED\n", timestamp_us());
  
    char const *str = "iecgw server";
    int n = socket_write_msg(newsockfd, 'I', 0, (uint8_t *)str, strlen(str));
    if (n < 0)
    {
      perror("ERROR writing to socket");
      close(newsockfd);
      return 1;
    }

    uint8_t buffer[256];
    uint8_t device_address;
    uint8_t cmd;
    size_t len = 256;
    int l = socket_read_msg(newsockfd, &cmd, &device_address, buffer, &len);
    if (l < 0 || cmd != 'I' || device_address > 31)
    {
      // Go away. Didn't know the magic word
      printf("%lld* protocol error\n", timestamp_us());
      close(newsockfd);
      return 1;
    }
    if (common->socketfds[device_address] >= 0) {
      printf("%lld* already allocated %d\n", timestamp_us(), device_address);
      close(newsockfd);
      return 1;
    }

    printf("%lld* DEVICE %d\n", timestamp_us(), (int)device_address);
    common->socketfds[device_address] = newsockfd;

    return 0;
}
