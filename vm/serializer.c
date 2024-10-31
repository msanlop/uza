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

#define PROG_CPY(dest, program, type) \
    do {                \
        dest = *((type*) program->bytes);      \
        program->count -= sizeof(type);      \
        program->bytes += sizeof(type);      \
    } while (0);        \



static inline void prog_read_bytes(void* dest, program_bytes_t* program, size_t elem_size, size_t elem_num) {
    memcpy(dest, program->bytes, elem_size * elem_num);
    program->count -= elem_size * elem_num;
    program->bytes += elem_size * elem_num;
}


void read_program_version(uint8_t* buff, program_bytes_t* program) {
    prog_read_bytes(buff, program, sizeof(uint8_t), 3);
}

void read_program(Chunk* chunk, program_bytes_t* program) {
    int endian_test = 1;
    system_is_little_endian = endian_test == ((char*) &endian_test)[0];
    uint8_t version[3] = {0};
    read_program_version(version, program);
    load_chunk(chunk, program);
}

void load_chunk(Chunk* chunk, program_bytes_t* program) {
    load_constants(&chunk->constants, program);
    uint16_t line = 0;
    while (program->count != 0) {
        PROG_CPY(line, program, uint16_t);
        if(!system_is_little_endian) line = REV_U16(line);
        load_op(chunk, line, program);
    }
}

void load_constants(ValueArray* array, program_bytes_t* program) {
    // 1 byte: the number of constants
    uint8_t constants_count = 0;
    PROG_CPY(constants_count, program, uint8_t);
    for (size_t i = 0; i < constants_count; i++) {
        // 1 byte: the ValueType
        uint8_t type_byte = 0;
        PROG_CPY(type_byte, program, uint8_t);
        ValueType type = (ValueType) type_byte;

        Value constant = {.type=type, .as.integer = 0};
        switch(type) {
            case TYPE_LONG:
                // 8 bytes: the int64 value
                PROG_CPY(constant.as.integer, program, int64_t);
                if(!system_is_little_endian) {
                    constant.as.integer = REV_U64(constant.as.integer);
                }
                break;
            case TYPE_DOUBLE:
                // 8 bytes: the float value
                prog_read_bytes(&(constant.as.fp), program, sizeof(double), 1);
                if(!system_is_little_endian) {
                    uint64_t temp = 0;
                    memcpy(&temp, &constant.as.fp, sizeof(double));
                    temp = REV_U64(temp);
                    memcpy(&constant.as.fp, &temp, sizeof(double));
                }
                break;
            case TYPE_BOOL:
                PROG_CPY(constant.as.boolean, program, bool);
                break;
            case TYPE_OBJ: {
                // 1 byte : object type
                uint8_t obj_type = 0;
                PROG_CPY(obj_type, program, uint8_t);

                if (((ObjectType) obj_type) == OBJ_STRING) {
                    //TODO: lower, have to make REV for that size
                    // 8 bytes: string length
                    uint64_t string_length = 0;
                    PROG_CPY(string_length, program, int64_t);
                    if(!system_is_little_endian) {
                        string_length = REV_U64(string_length);
                    }

                    // (string_length + 1) bytes: the string chars
                    ObjectString* const_pool_string = (ObjectString*)
                        calloc(sizeof(Obj) + sizeof(int) + string_length + 1, 1);
                    if(((ObjectType) obj_type) == OBJ_STRING) {
                        prog_read_bytes(const_pool_string->chars, program, sizeof(char), string_length);
                        const_pool_string->chars[string_length] = '\0';
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
void load_op(Chunk* chunk, uint16_t line, program_bytes_t* program) {
    OpCode opcode = 0;
    PROG_CPY(opcode, program, uint8_t);
    switch (opcode) {
        case OP_DCONST:
        case OP_STRCONST:
        case OP_LCONST:
            chunk_write(chunk, opcode, line);
            uint8_t constant_idx = 0;
            PROG_CPY(constant_idx, program, uint8_t);
            chunk_write(chunk, constant_idx, line);
            break;
        default:
            chunk_write(chunk, opcode, line);
            break;
    }
}
