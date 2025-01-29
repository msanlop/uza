#include <stdio.h>

#include "native.h"
#include "value.h"
#include "vm.h"

void native_println(void) {
    Value val = pop();
#ifndef NDEBUG
    fflush(stdout);
    DEBUG_PRINT(BRIGHT_RED "STDOUT PRINTLN:`" RESET);
    fflush(stderr);
#endif

    PRINT_VALUE(val, stdout);
    printf(NEWLINE);

#ifndef NDEBUG
    fflush(stdout);
    DEBUG_PRINT(BRIGHT_RED "`" RESET NEWLINE);
#endif
}

void native_print(void) {
    Value val = pop();
#ifndef NDEBUG
    fflush(stdout);
    DEBUG_PRINT(BRIGHT_RED "STDOUT PRINTLN:`" RESET);
    fflush(stderr);
#endif

    PRINT_VALUE(val, stdout);

#ifndef NDEBUG
    fflush(stdout);
    DEBUG_PRINT(BRIGHT_RED "`" RESET NEWLINE);
#endif
}

const NativeFunction native_builtins[] = {
    {"println", sizeof("println") - 1, {(native_function) native_println}, 1},
    {"print", sizeof("print") - 1, {(native_function) native_print}, 1},
};


const NativeFunction *const native_functions_get(size_t* out_count) {
    *out_count = sizeof(native_builtins) / sizeof(NativeFunction);
    return native_builtins;
}

// native functions
void native_println(void);
