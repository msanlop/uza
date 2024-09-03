#include "serializer.h"
#include "value.h"
#include "debug.h"
#include "string.h"


static bool system_is_little_endian;



#define SWAP_U16(value) ((value) = ((line << 8) & 0xFF00)|((line >> 8) & 0x00FF))

// Convert little endian to big endian. Use memcpy doubles before passing.
// Check for asm output, on clang any setting above -O1 outputs "rev". Otherwise
// it actually goes and does all the shifts.
uint64_t swap64(uint64_t value) {
    return ((value >> 56) & 0x00000000000000FFULL) |
           ((value >> 40) & 0x000000000000FF00ULL) |
           ((value >> 24) & 0x0000000000FF0000ULL) |
           ((value >> 8)  & 0x00000000FF000000ULL) |
           ((value << 8)  & 0x000000FF00000000ULL) |
           ((value << 24) & 0x0000FF0000000000ULL) |
           ((value << 40) & 0x00FF000000000000ULL) |
           ((value << 56) & 0xFF00000000000000ULL);
}

void read_program_version(uint8_t* buff, FILE* file) {
    fread(buff, sizeof(uint8_t), 3, file);
}

void read_program(Chunk* chunk, FILE* file) {
    int endian_test = 1;
    system_is_little_endian = endian_test == ((char*) &endian_test)[0];
    uint8_t version[3] = {0};
    read_program_version(version, file);
    load_chunk(chunk, file);
}

void load_chunk(Chunk* chunk, FILE* file) {
    load_constants(&chunk->constants, file);
    uint16_t line = 0;
    size_t read = fread(&line, sizeof(uint16_t), 1, file);
    if(!system_is_little_endian) line = SWAP_U16(line);
    while (read != 0) {
        load_op(chunk, line, file);
        read = fread(&line, sizeof(uint16_t), 1, file);
        if(!system_is_little_endian) SWAP_U16(line);
    }
}

void load_constants(ValueArray* array, FILE* file) {
    uint8_t constants_count = 0;
    fread(&constants_count, sizeof(uint8_t), 1, file);
    for (size_t i = 0; i < constants_count; i++) {
        uint8_t type_byte = 0;
        fread(&type_byte, 1, 1, file);
        ValueType type = (ValueType) type_byte;
        Value constant = {.type=type, .as.integer = 0};
        switch(type) {
            case TYPE_LONG:
                fread(&constant.as.integer, sizeof(int64_t), 1, file);
                if(!system_is_little_endian) {
                    constant.as.integer = swap64(constant.as.integer);
                }
                break;
            case TYPE_DOUBLE: 
                fread(&(constant.as.fp), sizeof(double), 1, file);
                if(!system_is_little_endian) {
                    uint64_t temp = 0;
                    memcpy(&temp, &constant.as.fp, sizeof(double));
                    temp = swap64(constant.as.fp);
                    memcpy(&constant.as.fp, &temp, sizeof(double));
                }
                break;
            case TYPE_BOOL: 
                fread(&constant.as.boolean, sizeof(bool), 1, file);
                break;
            default:
                break;
        } 

        value_array_write(array, constant);
    }
}
void load_op(Chunk* chunk, uint16_t line, FILE* file) {
    OpCode opcode = 0;
    fread(&opcode, sizeof(uint8_t), 1, file);
    switch (opcode) {
        case OP_DCONST:
        case OP_LCONST:
            chunk_write(chunk, opcode, line);
            uint8_t constant_idx = 0;
            fread(&constant_idx, sizeof(uint8_t), 1, file);
            chunk_write(chunk, constant_idx, line);
            break;
        default:
            chunk_write(chunk, opcode, line);
            break;
    }
}