#ifndef uza_common_h
#define uza_common_h

#ifdef DEBUG
    #define DEBUG_TRACE_EXECUTION_STACK
    #define DEBUG_TRACE_EXECUTION_OP
    #define PURPLE "\033[1;35m"
    #define YELLOW "\033[0;33m"
    #define RESET "\033[0m"
    #define DEBUG_PRINT(fmt, ...) \
        fprintf(stderr, PURPLE "DEBUG: " fmt RESET, ##__VA_ARGS__);
#endif


#include <stdbool.h>
#include <stdlib.h>

#define MIN(a, b) (a < b ? a : b)
#define MAX(a, b) (a > b ? a : b)

#define PRINT_ERR(string) (fprintf(stderr, string));

#endif // uza_common_h
