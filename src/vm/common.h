#ifndef uza_common_h
#define uza_common_h

#ifdef DEBUG
    #define DEBUG_TRACE_EXECUTION_STACK
    #define DEBUG_TRACE_EXECUTION_OP
    #define PURPLE "\033[1;35m"
    #define YELLOW "\033[0;33m"
    #define RESET "\033[0m"
    #define DEBUG_PRINT(fmt, ...) \
        fprintf(stderr, PURPLE fmt RESET, ##__VA_ARGS__);
#endif


#include <stdbool.h>
#include <stdlib.h>

#define MIN(a, b) (a < b ? a : b)
#define MAX(a, b) (a > b ? a : b)


#define PRINT_ERR(fmt, ...) \
            do { fprintf(stderr, "ERROR " fmt); } while (0)

#define PRINT_ERR_ARGS(fmt, ...) \
            do { fprintf(stderr, "ERROR " fmt, __VA_ARGS__); } while (0)

#endif // uza_common_h
