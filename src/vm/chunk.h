#ifndef uza_chunk_h
#define uza_chunk_h

#include "common.h"
#include "value.h"

typedef enum {
    OP_RETURN,
    OP_CONSTANT,
} OpCode;

typedef struct {
    size_t capacity;
    size_t count;
    ValueArray constants;
    uint16_t* lines;
    uint8_t* code;
} Chunk;

int print_opcode(Chunk* chunk, int offset);
void print_constant(char* code_str, Chunk* chunk, int offset);

Chunk* init_chunk_create();

void init_chunk(Chunk* chunk);
void free_chunk(Chunk* chunk);
void write_chunk(Chunk* chunk, OpCode opcode, uint16_t line);
void print_chunk(Chunk* chunk);
int add_constant(Chunk* chunk, Value constant);

#endif // uza_chunk_h
