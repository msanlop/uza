#ifndef uza_chunk_h
#define uza_chunk_h

#include "common.h"
#include "value.h"
#include "bytecodes.h"
#include "stdint.h"

typedef struct {
    size_t capacity;
    size_t count;
    ValueArray constants;
    uint16_t* lines;
    uint8_t* code;
} Chunk;

#define GET_LINE_AT(chunk_ptr, offset) (chunk_ptr->lines[offset])
#define GET_CODE_AT(chunk_ptr, offset) (chunk_ptr->code[offset])
#define GET_CODE_AT_CAST(type, chunk_ptr, offset) (*(type*) &chunk_ptr->code[offset])


#define CHUNK_WRITE(type, value, line) { \
    size_t capacity_new = 0; \
    if(chunk->count + sizeof(type) > chunk->capacity) { \
        capacity_new = GROW_CAPACITY(chunk->capacity); \
        uint8_t* code_new = GROW_ARRAY(uint8_t, chunk->code, chunk->capacity, capacity_new); \
        uint16_t* lines_new = GROW_ARRAY(uint16_t, chunk->lines, chunk->capacity, capacity_new); \
	chunk->code = code_new; \
        chunk->lines = lines_new; \
    	chunk->capacity = capacity_new; \
    } \
    *(type*)(&chunk->code[chunk->count]) = value; \
    chunk->lines[chunk->count] = line; \
    chunk->count += sizeof(type); \
}

void chunk_init(Chunk* chunk);
void chunk_free(Chunk* chunk);
int  chunk_const_add(Chunk* chunk, Value constant);

#endif // uza_chunk_h
