#ifndef uza_common_h
#define uza_common_h

#ifdef DEBUG
    #define DEBUG_TRACE_EXECUTION_STACK
    #define DEBUG_TRACE_EXECUTION_OP
    #define DEBUG_DUMP_VM
    #define PURPLE "\033[1;35m"
    #define YELLOW "\033[0;33m"
    #define RESET "\033[0m"
    #define RESET "\033[0m"
    #define BLACK "\033[0;30m"
    #define RED "\033[0;31m"
    #define GREEN "\033[0;32m"
    #define YELLOW "\033[0;33m"
    #define BLUE "\033[0;34m"
    #define MAGENTA "\033[0;35m"
    #define CYAN "\033[0;36m"
    #define WHITE "\033[0;37m"
    #define BRIGHT_BLACK "\033[1;30m"
    #define BRIGHT_RED "\033[1;31m"
    #define BRIGHT_GREEN "\033[1;32m"
    #define BRIGHT_YELLOW "\033[1;33m"
    #define BRIGHT_BLUE "\033[1;34m"
    #define BRIGHT_MAGENTA "\033[1;35m"
    #define BRIGHT_CYAN "\033[1;36m"
    #define BRIGHT_WHITE "\033[1;37m"
    #define DEBUG_PRINT_COL(fmt, ...) \
        fprintf(stderr, PURPLE fmt RESET, ##__VA_ARGS__);
    #define DEBUG_PRINT(fmt, ...) \
        fprintf(stderr, fmt, ##__VA_ARGS__);
#endif


#include <stdbool.h>
#include <stdlib.h>
#include <stdint.h>

#define MIN(a, b) (a < b ? a : b)
#define MAX(a, b) (a > b ? a : b)


#define PRINT_ERR(fmt, ...) \
            do { fprintf(stderr, "ERROR " fmt); } while (0)

#define PRINT_ERR_ARGS(fmt, ...) \
            do { fprintf(stderr, "ERROR " fmt, __VA_ARGS__); } while (0)

typedef struct {
    size_t count;
    uint8_t* bytes;
} program_bytes_t;

#endif // uza_common_h
