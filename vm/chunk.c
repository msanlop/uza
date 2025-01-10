
#include "common.h"
#include "chunk.h"
#include "memory.h"
#include <stdio.h>



void chunk_init(Chunk* chunk) {
    chunk->capacity = 0;
    chunk->count = 0;
    chunk->code = NULL;
    chunk->count = 0;
    value_array_init(&chunk->constants);
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
