#include "must.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>

void _must(const char *fileName, int lineNumber, const char *funcName,
           const char *calledFunction, int err) {
  if (err < 0) {
    char buf[256];
    snprintf(buf, 256, "%s:%d in %s: %s: [%d]", fileName, lineNumber, funcName,
             calledFunction, errno);
    perror(buf);
    exit(1);
  }
}
