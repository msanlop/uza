
#include "common.h"
#include "chunk.h"
#include "memory.h"
#include <stdio.h>


int print_opcode(OpCode op) {
    switch (op)
    {
    case OP_RETURN:
        printf("OP_RETURN");
        return 1;
        break;
    case OP_CONSTANT:
        printf("OP_CONSTANT");
        return 2;
        break;
    default:
        break;
    }
}

void print_constant(char* code_str, Chunk* chunk, int offset){
    printf("%s    ", code_str);
    int constant = chunk->code[offset + 1];
    Value val = chunk->constants.values[constant];
    printf("%s    ", code_str);
    printf("'%lf'\n", val);
}

void init_chunk(Chunk* chunk) {
    chunk->capacity = 0;
    chunk->count = 0;
    chunk->code = NULL;
    init_valueArray(&chunk->constants);
}

void write_chunk(Chunk* chunk, OpCode opcode) {
    size_t capacity_new = 0;
    if(chunk->count + 1 > chunk->capacity) {
        capacity_new = GROW_CAPACITY(chunk->capacity);
        uint8_t* code_new = GROW_ARRAY(uint8_t, chunk->code, chunk->capacity, capacity_new);
        chunk->code = (uint8_t*) code_new;
        chunk->capacity = capacity_new;
    }
    chunk->code[chunk->count] = opcode;
    chunk->count += 1;
}

void free_chunk(Chunk* chunk) {
    FREE_ARRAY(uint8_t, chunk->code, chunk->count);
    free_valueArray(&chunk->constants);
    init_chunk(chunk);
}

void print_chunk(Chunk* chunk) {
    printf("Chunk(\n");
    for (size_t offset = 0; offset < chunk->count;)
    {
        printf("%04zu  ", offset);
        offset += print_opcode(chunk->code[offset]);
        printf("\n");
    }
    
    printf(")\n");
}

int add_constant(Chunk* chunk, Value constant) {
    write_valueArray(&chunk->constants, constant);
    return chunk->constants.count;
}