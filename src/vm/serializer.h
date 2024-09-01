#ifndef uza_serializer_h
#define uza_serializer_h

#include "common.h"
#include "chunk.h"
#include "stdio.h"


// void load_program(FILE* file, Chunk* chunk);
void load_chunk(Chunk* chunk, FILE* file);
void load_constants(ValueArray *array, FILE* file);
void load_op(Chunk* chunk, uint16_t line, FILE* file);


#endif // uza_serializer_h
