#include "vm.h"
#include <stdio.h>

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
    VM* vm = init_vm(file);
    fclose(file);
    if (vm == NULL) {
        fprintf(stderr, "VM is null");
        free_vm(vm);
        return 1;
    }

    dump_vm(vm);
    free_vm(vm);
    return 0;
}