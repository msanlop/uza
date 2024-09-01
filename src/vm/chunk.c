
#include "common.h"
#include "chunk.h"
#include "memory.h"
#include <stdio.h>


int print_opcode(Chunk* chunk, int offset) {
    uint16_t line = chunk->lines[offset];
    if(offset>0 && chunk->lines[offset] == line) {
        printf("    |  ");
    } else {
        printf("%5d  ", line);
    }
    switch (chunk->code[offset])
    {
    case OP_RETURN:
        printf("OP_RETURN");
        return 1;
        break;
    case OP_CONSTANT:
        print_constant("OP_CONSTANT", chunk, offset);
        return 2;
        break;
    default:
        break;
    }
    PRINT_ERR("OP CODE NOT FOUND")
    exit(1);
}

void print_constant(char* code_str, Chunk* chunk, int offset){
    printf("%s    ", code_str);
    int constant = chunk->code[offset + 1];
    Value val = chunk->constants.values[constant];
    printf("'%.3lf'", val);
}

void init_chunk(Chunk* chunk) {
    chunk->capacity = 0;
    chunk->count = 0;
    chunk->code = NULL;
    init_valueArray(&chunk->constants);
}

Chunk* init_chunk_create() {
    Chunk _chunk = {0};
    Chunk* chunk = &_chunk;
    chunk->capacity = 0;
    chunk->count = 0;
    chunk->code = NULL;
    init_valueArray(&chunk->constants);
    return chunk;
}

void write_chunk(Chunk* chunk, OpCode opcode, uint16_t line) {
    size_t capacity_new = 0;
    if(chunk->count + 1 > chunk->capacity) {
        capacity_new = GROW_CAPACITY(chunk->capacity);
        uint8_t* code_new = GROW_ARRAY(uint8_t, chunk->code, chunk->capacity, capacity_new);
        uint16_t* lines_new = GROW_ARRAY(uint16_t, chunk->lines, chunk->capacity, capacity_new);
        chunk->code = code_new;
        chunk->lines = lines_new;
        chunk->capacity = capacity_new;
    }
    chunk->code[chunk->count] = opcode;
    chunk->lines[chunk->count] = line;
    chunk->count += 1;
}

void free_chunk(Chunk* chunk) {
    FREE_ARRAY(uint8_t, chunk->code, chunk->count);
    free_valueArray(&chunk->constants);
    init_chunk(chunk);
}

void print_chunk(Chunk* chunk) {
    printf("/// Chunk ///\n");
    for (size_t offset = 0; offset < chunk->count;)
    {
        printf("%04zu  ", offset);
        int incr = print_opcode(chunk, offset);
        offset+=incr;
        printf("\n");
    }
    
}

int add_constant(Chunk* chunk, Value constant) {
    write_valueArray(&chunk->constants, constant);
    return chunk->constants.count;
}