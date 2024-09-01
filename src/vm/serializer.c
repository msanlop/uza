#include "serializer.h"

void load_chunk(Chunk* chunk, FILE* file) {
    load_constants(&chunk->constants, file);
    uint16_t line = 0;
    size_t read = fread(&line, sizeof(uint8_t), 2, file);
    while(read != 0) {
        load_op(chunk, line, file);
        read = fread(&line, sizeof(uint8_t), 2, file);
    }
}

void load_constants(ValueArray *array, FILE* file){
    uint8_t constants_count = 0;
    fread(&constants_count, sizeof(uint8_t), 1, file);
    for (size_t i = 0; i < constants_count; i++) {
        Value constant = 0;
        fread(&constant, sizeof(Value), 1, file);
        write_valueArray(array, constant);
    }
    
}
void load_op(Chunk* chunk, uint16_t line, FILE* file) {
    OpCode opcode = OP_RETURN;
    fread(&opcode, sizeof(uint8_t), 1, file);
    switch (opcode)
    {
    case OP_RETURN:
        write_chunk(chunk, OP_RETURN, line);
        break;
    case OP_CONSTANT:
        write_chunk(chunk, OP_CONSTANT, line);
        uint8_t constant_idx = 0;
        fread(&constant_idx, sizeof(uint8_t), 1, file);
        write_chunk(chunk, constant_idx, line);
        break;
    default:
        break;
    }
}