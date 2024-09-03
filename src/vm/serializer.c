#include "serializer.h"

void read_program_version(uint8_t* buff, FILE* file) {
    fread(buff, sizeof(uint8_t), 3, file);
}

void read_program(Chunk* chunk, FILE* file) {
    uint8_t version[3] = {0};
    read_program_version(version, file);
    load_chunk(chunk, file);
}

void load_chunk(Chunk* chunk, FILE* file) {
    load_constants(&chunk->constants, file);
    uint16_t line = 0;
    size_t read = fread(&line, sizeof(uint8_t), 2, file);
    while (read != 0) {
        load_op(chunk, line, file);
        read = fread(&line, sizeof(uint8_t), 2, file);
    }
}

void load_constants(ValueArray* array, FILE* file) {
    uint8_t constants_count = 0;
    fread(&constants_count, sizeof(uint8_t), 1, file);
    for (size_t i = 0; i < constants_count; i++) {
        Value constant = 0;
        fread(&constant, sizeof(Value), 1, file);
        value_array_write(array, constant);
    }
}
void load_op(Chunk* chunk, uint16_t line, FILE* file) {
    OpCode opcode = 0;
    fread(&opcode, sizeof(uint8_t), 1, file);
    switch (opcode) {
        case OP_LOAD_CONST:
            chunk_write(chunk, OP_LOAD_CONST, line);
            uint8_t constant_idx = 0;
            fread(&constant_idx, sizeof(uint8_t), 1, file);
            chunk_write(chunk, constant_idx, line);
            break;
        default:
            chunk_write(chunk, opcode, line);
            break;
    }
}