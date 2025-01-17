
#include "common.h"
#include "chunk.h"
#include "memory.h"
#include "object.h"
#include <stdio.h>



Chunk* chunk_init() {
    Chunk *chunk = calloc(1, sizeof(Chunk));
    chunk->local_count = 0;
    chunk->count = 0;
    chunk->code = NULL;
    chunk->count = 0;
    value_array_init(&chunk->constants);
    return chunk;
}


void chunk_free(Chunk* chunk) {
    // FREE_ARRAY(uint8_t, chunk->code, chunk->count);
    if (chunk->constants.values != NULL) {
        for(size_t i = 0; i < chunk->constants.capacity; i++) {
            Value *val = &chunk->constants.values[i];
            ARC_DECREMENT(*val);
        }
    }
    value_array_free(&chunk->constants);
    free(chunk);
}


int chunk_const_add(Chunk* chunk, Value constant) {
    value_array_write(&chunk->constants, constant);
    return chunk->constants.count;
}
