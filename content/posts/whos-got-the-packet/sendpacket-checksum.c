#include <arpa/inet.h>
#include <fcntl.h>
#include <linux/if.h>
#include <linux/if_tun.h>
#include <netinet/in.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define must(x) _must(#x, __FILE__, __LINE__, __func__, (x))

void _must(const char *call, const char *filename, int line,
           const char *funcname, int err) {
  char buf[1024];
  snprintf(buf, 1023, "%s (@ %s:%d)", call, filename, line);
  if (err < 0) {
    perror(buf);
    exit(1);
  }
}

static int tunAlloc(void) {
  int fd;
  struct ifreq ifr = {.ifr_name = "tun0", .ifr_flags = IFF_TUN | IFF_NO_PI};

  fd = open("/dev/net/tun", O_RDWR);
  must(ioctl(fd, TUNSETIFF, (void *)&ifr));
  must(ioctl(fd, TUNSETOWNER, geteuid()));
  return fd;
}

static void bringInterfaceUp(void) {
  int sock;
  struct sockaddr_in addr = {.sin_family = AF_INET};
  struct ifreq ifr = {.ifr_name = "tun0"};

  inet_aton("172.30.0.1", &addr.sin_addr);
  memcpy(&ifr.ifr_addr, &addr, sizeof(struct sockaddr));

  sock = socket(AF_INET, SOCK_DGRAM, 0);
  must(ioctl(sock, SIOCSIFADDR, &ifr));
  must(ioctl(sock, SIOCGIFFLAGS, &ifr));
  ifr.ifr_flags |= IFF_UP | IFF_RUNNING;
  must(ioctl(sock, SIOCSIFFLAGS, &ifr));
  close(sock);
}

static void emitPacket(int tap_fd) {
  uint16_t cs;
  uint8_t packet[] = {
      0x45, 0x00, 0x00, 0x3c, 0xd8, 0x6f, 0x40, 0x00, 0x3f, 0x06, 0xf7, 0x7b,
      172,  30,   0,    1,    192,  168,  255,  8,    0xa2, 0x9a, 0x27, 0x11,
      0x80, 0x0b, 0x63, 0x79, 0x00, 0x00, 0x00, 0x00, 0xa0, 0x02, 0xfa, 0xf0,
      0x78, 0xc3, 0x00, 0x00, 0x02, 0x04, 0x05, 0xb4, 0x04, 0x02, 0x08, 0x0a,
      0x5b, 0x76, 0x5f, 0xd4, 0x00, 0x00, 0x00, 0x00, 0x01, 0x03, 0x03, 0x07,
  };

  write(tap_fd, packet, sizeof(packet));
}

void prompt(char *promptString) {
  printf("%s\n", promptString);
  getchar();
}

int main() {
  int tap_fd;

  tap_fd = tunAlloc();

  bringInterfaceUp();
  prompt("interface is up");
  emitPacket(tap_fd);
  prompt("sent packet");
  close(tap_fd);
  printf("all done");

  return 0;
}
