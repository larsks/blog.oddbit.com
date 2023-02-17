
#ifndef _MUST
#define _MUST

#define must(x) _must(__FILE__, __LINE__, __func__, #x, (x))

void _must(const char *fileName, int lineNumber, const char *funcName,
           const char *calledFunction, int err);
#endif
