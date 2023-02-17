#include "must.h"
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>

int main() {
  int fd;
  char buf[1024];

  printf("opening a file that does exist\n");
  must(fd = open("file-that-exists.txt", O_RDONLY));

  while (1) {
    int nb;
    must(nb = read(fd, buf, sizeof(buf)));
    if (!nb)
      break;
    must(write(STDOUT_FILENO, buf, nb));
  }

  must(close(fd));

  printf("opening a file that doesn't exist\n");
  must(fd = open("file-that-does-not-exist.xt", O_RDONLY));
  return 0;
}
