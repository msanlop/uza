#if !defined(uza_common_h)
#define uza_common_h

#include <stdbool.h>
#include <stdlib.h>

#define MIN(a, b) (a < b ? a : b)
#define MAX(a, b) (a > b ? a : b)

#define PRINT_ERR(string) (fprintf(stderr, string));

#endif // uza_common_h
