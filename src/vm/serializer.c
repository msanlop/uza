#include "serializer.h"
#include "value.h"
#include "debug.h"
#include "string.h"
#include "memory.h"


static bool system_is_little_endian;


#define REV_U16(value) (((line << 8) & 0xFF00)|((line >> 8) & 0x00FF))

// Convert little endian to big endian. Use memcpy for double before passing.
// Check for asm output, on clang any setting above -O1 outputs "rev". Otherwise
// it actually goes and does all the shifts.
#define REV_U64(value) \
           ((((value) >> 56) & 0x00000000000000FFULL) | \
           (((value) >> 40) & 0x000000000000FF00ULL) | \
           (((value) >> 24) & 0x0000000000FF0000ULL) | \
           (((value) >> 8)  & 0x00000000FF000000ULL) | \
           (((value) << 8)  & 0x000000FF00000000ULL) | \
           (((value) << 24) & 0x0000FF0000000000ULL) | \
           (((value) << 40) & 0x00FF000000000000ULL) | \
           (((value) << 56) & 0xFF00000000000000ULL)) \


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
    if(!system_is_little_endian) line = REV_U16(line);
    while (read != 0) {
        load_op(chunk, line, file);
        read = fread(&line, sizeof(uint16_t), 1, file);
        if(!system_is_little_endian) REV_U16(line);
    }
}

void load_constants(ValueArray* array, FILE* file) {
    // 1 byte: the number of constants
    uint8_t constants_count = 0;
    fread(&constants_count, sizeof(uint8_t), 1, file);
    for (size_t i = 0; i < constants_count; i++) {
        // 1 byte: the ValueType
        uint8_t type_byte = 0;
        fread(&type_byte, 1, 1, file);
        ValueType type = (ValueType) type_byte;
        
        Value constant = {.type=type, .as.integer = 0};
        switch(type) {
            case TYPE_LONG:
                // 8 bytes: the int64 value
                fread(&constant.as.integer, sizeof(int64_t), 1, file);
                if(!system_is_little_endian) {
                    constant.as.integer = REV_U64(constant.as.integer);
                }
                break;
            case TYPE_DOUBLE: 
                // 8 bytes: the float value
                fread(&(constant.as.fp), sizeof(double), 1, file);
                if(!system_is_little_endian) {
                    uint64_t temp = 0;
                    memcpy(&temp, &constant.as.fp, sizeof(double));
                    temp = REV_U64(temp);
                    memcpy(&constant.as.fp, &temp, sizeof(double));
                }
                break;
            case TYPE_BOOL: 
                fread(&constant.as.boolean, sizeof(bool), 1, file);
                break;
            case TYPE_OBJ: {
                // 1 byte : object type
                uint8_t obj_type = 0;
                fread(&obj_type, sizeof(uint8_t), 1, file);
                
                if (((ObjectType) obj_type) == OBJ_STRING) {
                    //TODO: lower, have to make REV for that size
                    // 8 bytes: string length 
                    uint64_t string_length = 0;
                    fread(&string_length, sizeof(int64_t), 1, file);
                    if(!system_is_little_endian) {
                        string_length = REV_U64(string_length);
                    }
                    
                    // (string_length + 1) bytes: the string chars
                    ObjectString* const_pool_string = (ObjectString*) 
                        calloc(sizeof(Obj) + sizeof(int) + string_length + 1, 1);
                    if(((ObjectType) obj_type) == OBJ_STRING) {
                        fgets(const_pool_string->chars, string_length+1, file);
                    }

                    const_pool_string->length = string_length;
                    const_pool_string->obj.type = OBJ_STRING;
                    constant.type = TYPE_OBJ;
                    constant.as.object = (Obj*) const_pool_string;
                }
                else {
                    PRINT_ERR_ARGS("unrecognized object type : %d", obj_type);
                    exit(1);
                }
                break;
            }
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
        case OP_STRCONST:
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
