#ifndef uza_serialize_h
#define uza_serialize_h

#include "chunk.h"
#include "common.h"
#include "stdio.h"
#include "vm.h"

/*

All bytecode is in LITTLE endian.
The bytecode is structered as follows, where 1B == 1 byte:

### FILE HEADERS ###
TODO:  MAGIC number :)
3B : 3 version numbers
4B : chunk count

for each CHUNK
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

    1B  : number_of_locals

    ### OPCODES ###
    2B : bytecode count (number of ops)
    2B : bytecode length (number of bytes for the code)

    for each opcode
        1B   : OpCode
        (1B) : constant if needed
        (1B) : local variable index

    for i in range( _bytecode count_ ):
        2B   : line number

*/

// void load_program(FILE* file, VM *vm);
void load_chunk(size_t chunk_idx, program_bytes_t *program);
void load_constants(ValueArray *array, program_bytes_t *program,
                    Table *strings);
void load_op(size_t chunk_idx, uint16_t line, program_bytes_t *program);

void read_program_version(uint8_t *buff, program_bytes_t *program);
void read_program(program_bytes_t *program);

#endif // uza_serialize_h
