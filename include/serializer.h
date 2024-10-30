#ifndef uza_serializer_h
#define uza_serializer_h

#include "common.h"
#include "chunk.h"
#include "stdio.h"

/*

All bytecode is in LITTLE endian.
The bytecode is structered as follows, where 1B == 1 byte:

### FILE HEADERS ###
TODO:  MAGIC number :)
3B : 3 version numbers

### CONSTANTS ###
1B  : number_of_constants

for each CONSTANT
    1B: ValueType
    case OBJECT:
        1B           : ObjectType
        8B           : string length
        (str_len)B : String chars (not null terminated)

    case INT    : 8B
    case DOUBLE : 8B

### OPCODES ###
for each opcode
    2B   : line number
    1B   : OpCode
    (1B) : constant if needed

*/

// void load_program(FILE* file, Chunk* chunk);
void load_chunk(Chunk* chunk, program_bytes_t* program);
void load_constants(ValueArray *array, program_bytes_t* program);
void load_op(Chunk* chunk, uint16_t line, program_bytes_t* program);

void read_program_version(uint8_t* buff, program_bytes_t* program);
void read_program(Chunk* chunk, program_bytes_t* program);

#endif // uza_serializer_h
