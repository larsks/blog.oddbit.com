#include <arpa/inet.h>
#include <fcntl.h>
#include <linux/if.h>
#include <linux/if_tun.h>
#include <netinet/in.h>
#include <poll.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

static int tunAlloc(void) {
  int fd;
  struct ifreq ifr = {.ifr_name = "tun0", .ifr_flags = IFF_TUN | IFF_NO_PI};

  fd = open("/dev/net/tun", O_RDWR);
  ioctl(fd, TUNSETIFF, (void *)&ifr);
  ioctl(fd, TUNSETOWNER, geteuid());
  return fd;
}

// this is a test
static void bringInterfaceUp(void) {
  int sock;
  struct sockaddr_in addr = {.sin_family = AF_INET};
  struct ifreq ifr = {.ifr_name = "tun0"};

  inet_aton("172.30.0.1", &addr.sin_addr);
  memcpy(&ifr.ifr_addr, &addr, sizeof(struct sockaddr));

  sock = socket(AF_INET, SOCK_DGRAM, 0);
  ioctl(sock, SIOCSIFADDR, &ifr);
  ioctl(sock, SIOCGIFFLAGS, &ifr);
  ifr.ifr_flags |= IFF_UP | IFF_RUNNING;
  ioctl(sock, SIOCSIFFLAGS, &ifr);
  close(sock);
}

static void emitPacket(int tap_fd) {
  unsigned char packet[] = {
      0x45, 0x00, 0x00, 0x3c, 0xd8, 0x6f, 0x40, 0x00, 0x3f, 0x06, 0x08, 0x91,
      172,  30,   0,    1,    192,  168,  255,  8,    0xa2, 0x9a, 0x27, 0x11,
      0x80, 0x0b, 0x63, 0x79, 0x00, 0x00, 0x00, 0x00, 0xa0, 0x02, 0xfa, 0xf0,
      0x89, 0xd8, 0x00, 0x00, 0x02, 0x04, 0x05, 0xb4, 0x04, 0x02, 0x08, 0x0a,
      0x5b, 0x76, 0x5f, 0xd4, 0x00, 0x00, 0x00, 0x00, 0x01, 0x03, 0x03, 0x07};

  write(tap_fd, packet, sizeof(packet));
}

int main() {
  int tap_fd;

  tap_fd = tunAlloc();
  bringInterfaceUp();
  emitPacket(tap_fd);
  close(tap_fd);

  return 0;
}
