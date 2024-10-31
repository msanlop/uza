#include "vm.h"
#include <stdio.h>
#include "debug.h"
#include <string.h>

int test_print(int a, char** words) {
    printf("%s", words[0]);
    printf("%s", words[1]);
    return a;
}


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
        interpret(vm);
        debug_vm_dump(vm);
    #else
        interpret(vm);
    #endif
    vm_free(vm);
    // fflush(stdout);
    // fflush(stderr);
    return 0;
}

int main(int argc, char** argv) {
    if (argc != 3){
        fprintf(stderr, "Expected 2 arguments, got %d\n", argc-1);
        return 1;
    }
    FILE* file = fopen(argv[2], "r");
    if (file == NULL) {
        fprintf(stderr, "FILE NOT FOUND");
        return 1;
    }

    int program_len = atoi(argv[1]);
    char bytes[program_len];
    fread(bytes, 1, program_len, file);
    fclose(file);

    return run_vm(program_len, bytes);
}
