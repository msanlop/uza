#include "vm.h"
#include <stdio.h>
#include "debug.h"

int main(int argc, char** argv) {
    if (argc != 2){
        fprintf(stderr, "Expected 1 argumet, got %d\n", argc);
        return 1;
    }
    FILE* file = fopen(argv[1], "r");
    if (file == NULL) {
        fprintf(stderr, "FILE NOT FOUND");
        return 1;
    }
    VM* vm = vm_init(file);
    fclose(file);
    if (vm == NULL) {
        fprintf(stderr, "VM is null");
        vm_free(vm);
        return 1;
    }

    #ifdef DEBUG
        debug_vm_dump(vm);
        interpret(vm);
        debug_vm_dump(vm);
    #else
        interpret(vm);
    #endif
    vm_free(vm);
    return 0;
}