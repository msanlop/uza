
#include "common.h"
#include "chunk.h"
#include "memory.h"
#include <stdio.h>





void chunk_init(Chunk* chunk) {
    chunk->capacity = 0;
    chunk->count = 0;
    chunk->code = NULL;
    value_array_init(&chunk->constants);
}

void chunk_write(Chunk* chunk, OpCode opcode, uint16_t line) {
    size_t capacity_new = 0;
    if(chunk->count + 1 > chunk->capacity) {
        capacity_new = GROW_CAPACITY(chunk->capacity);
        uint8_t* code_new = GROW_ARRAY(uint8_t, chunk->code, chunk->capacity, capacity_new);
        uint16_t* lines_new = GROW_ARRAY(uint16_t, chunk->lines, chunk->capacity, capacity_new);
        chunk->code = code_new;
        chunk->lines = lines_new;
    }
    chunk->code[chunk->count] = opcode;
    chunk->lines[chunk->count] = line;
    chunk->lines[chunk->count] = line;
    chunk->count += 1;
}

void chunk_free(Chunk* chunk) {
    FREE_ARRAY(uint8_t, chunk->code, chunk->count);
    value_array_free(&chunk->constants);
    chunk_init(chunk);
}


int chunk_const_add(Chunk* chunk, Value constant) {
    value_array_write(&chunk->constants, constant);
    return chunk->constants.count;
}