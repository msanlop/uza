#include "vm.h"
#include <stdio.h>
#include "debug.h"
#include <string.h>

int test_print(int a, char** words) {
    printf("%s", words[0]);
    printf("%s", words[1]);
    return a;
}

#if defined(_WIN32) || defined(WIN32)
__declspec(dllexport)
#endif
int run_vm(int byte_count, char* code) {
    program_bytes_t program = {byte_count, code};

    VM* vm = vm_init(&program);
    if (vm == NULL) {
        fprintf(stderr, "VM is null");
        vm_free(vm);
        return 1;
    }

    #ifdef DEBUG_DUMP_VM
        debug_vm_dump(vm);
    int res = interpret(vm);
        debug_vm_dump(vm);
    #else
    int res = interpret(vm);
    #endif
    vm_free(vm);
    // fflush(stdout);
    // fflush(stderr);
    return res;
}

