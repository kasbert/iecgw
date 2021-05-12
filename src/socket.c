#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <fcntl.h>
#include <sys/select.h>
#include <sys/ioctl.h>
#include <netdb.h>
#include <netinet/in.h>

#include "socketproto.h"

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


int socket_read_msg(int fd, char *cmd, uint8_t *secondary, uint8_t *buffer, size_t *size)
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

int socket_read_buf(int fd, char *buf, size_t len)
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

int socket_write_msg(int fd, char cmd, uint8_t secondary, uint8_t *buffer, uint8_t size)
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

int socket_write_buf(int fd, char *buf, size_t len)
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

int socket_init_server()
{
  int portno;
  struct sockaddr_in serv_addr;

  int sockfd = socket(AF_INET, SOCK_STREAM, 0);

  if (sockfd < 0)
  {
    perror("socket_init_server socket");
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
    perror("socket_init_server bind");
    return -1;
  }

  listen(sockfd, 1);
  return sockfd;
}

int socket_accept(int fd) {
    struct sockaddr_in cli_addr;
    socklen_t clilen = sizeof(cli_addr);
    int newsockfd = accept(fd, (struct sockaddr *)&cli_addr, &clilen);
    return newsockfd;
}

