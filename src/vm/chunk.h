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

void chunk_init(Chunk* chunk);
void chunk_free(Chunk* chunk);
void chunk_write(Chunk* chunk, OpCode opcode, uint16_t line);
int  chunk_const_add(Chunk* chunk, Value constant);

#endif // uza_chunk_h
