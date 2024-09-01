#ifndef uza_serializer_h
#define uza_serializer_h

#include "common.h"
#include "chunk.h"
#include "stdio.h"


// void load_program(FILE* file, Chunk* chunk);
void load_chunk(FILE* file, Chunk* chunk);
void load_constants(FILE* file, ValueArray *array);
void load_op(FILE* file, Chunk* chunk, uint16_t line);


#endif // uza_serializer_h
