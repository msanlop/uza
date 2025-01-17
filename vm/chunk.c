
#include "common.h"
#include "chunk.h"
#include "memory.h"
#include "object.h"
#include <stdio.h>



void chunk_init(Chunk* chunk) {
    chunk->local_count = 0;
    chunk->count = 0;
    chunk->code = NULL;
    chunk->count = 0;
    value_array_init(&chunk->constants);
}


void chunk_free(Chunk* chunk) {
    // FREE_ARRAY(uint8_t, chunk->code, chunk->count);
    // for(size_t i = 0; chunk->constants.capacity; i++) {
    //     Value *val = &chunk->constants.values[i];
    //     if (val != NULL && IS_OBJECT(*val)) {
    //         object_free(val);
    //     }
    // }
    value_array_free(&chunk->constants);
    chunk_init(chunk);
}


int chunk_const_add(Chunk* chunk, Value constant) {
    value_array_write(&chunk->constants, constant);
    return chunk->constants.count;
}
