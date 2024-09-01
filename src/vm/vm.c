#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "chunk.h"
#include "common.h"
#include "serializer.h"
#include "vm.h"

void read_program_version(uint8_t* buff, FILE* file) {
    fread(buff, sizeof(uint8_t), 3, file);
}

void read_program(Chunk* chunk, FILE* file) {

    uint8_t version[3] = {0};
    read_program_version(version, file);
    load_chunk(chunk, file);
}


VM* init_vm(FILE* file) { 
    VM* vm = calloc(1, sizeof(VM));
    if (vm == NULL) return vm;
    read_program(&vm->chunk, file);
    vm->ip = vm->chunk.code;
    return vm;
}

void dump_vm(VM* vm) { 
    printf("///  VM   ///\n");
    printf("%s", vm->ip);
    print_chunk(&vm->chunk);
    printf("/////////////\n");
}

void free_vm(VM* vm){
    free_chunk(&vm->chunk);
    free(vm);
}