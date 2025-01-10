#include <stdio.h>

#include "native.h"
#include "value.h"
#include "vm.h"

void native_println(void * vm_ptr) {
    VM * vm = (VM *) vm_ptr;
    Value val = pop((VM *) vm);
    DEBUG_PRINT("STDOUT PRINTLN: ");
    PRINT_VALUE(val, stdout);
    printf(NEWLINE);
}

const NativeFunction native_builtins[] = {
    {"println", sizeof("println") - 1, {(native_function) native_println}, 1},
};


const NativeFunction *const native_functions_get(size_t* out_count) {
    *out_count = sizeof(native_builtins) / sizeof(NativeFunction);
    return native_builtins;
}
