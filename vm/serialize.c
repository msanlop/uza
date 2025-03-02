#include <assert.h>

#include "debug.h"
#include "memory.h"
#include "serialize.h"
#include "string.h"
#include "value.h"

static bool system_is_little_endian;

#define REV_U16(value) (((line << 8) & 0xFF00) | ((line >> 8) & 0x00FF))

// Convert little endian to big endian. Use memcpy for double before passing.
// Check for asm output, on clang any setting above -O1 outputs "rev". Otherwise
// it actually goes and does all the shifts.
#define REV_U64(value)                                                         \
  ((((value) >> 56) & 0x00000000000000FFULL) |                                 \
   (((value) >> 40) & 0x000000000000FF00ULL) |                                 \
   (((value) >> 24) & 0x0000000000FF0000ULL) |                                 \
   (((value) >> 8) & 0x00000000FF000000ULL) |                                  \
   (((value) << 8) & 0x000000FF00000000ULL) |                                  \
   (((value) << 24) & 0x0000FF0000000000ULL) |                                 \
   (((value) << 40) & 0x00FF000000000000ULL) |                                 \
   (((value) << 56) & 0xFF00000000000000ULL))

#define PROG_CPY(dest, program, type)                                          \
  do {                                                                         \
    dest = *((type *)program->bytes);                                          \
    program->count -= sizeof(type);                                            \
    program->bytes += sizeof(type);                                            \
  } while (0);

static inline void prog_read_bytes(void *dest, program_bytes_t *program,
                                   size_t elem_size, size_t elem_num) {
  memcpy(dest, program->bytes, elem_size * elem_num);
  program->count -= elem_size * elem_num;
  program->bytes += elem_size * elem_num;
}

void read_program_version(uint8_t *buff, program_bytes_t *program) {
  prog_read_bytes(buff, program, sizeof(uint8_t), 3);
}

void read_program(program_bytes_t *program) {
  int endian_test = 1;
  system_is_little_endian = endian_test == ((char *)&endian_test)[0];
  uint8_t version[3] = {0};
  read_program_version(version, program);
  uint32_t chunk_count = 0;
  PROG_CPY(chunk_count, program, uint32_t);

  vm.chunk_count = chunk_count;
  vm.chunks = calloc(chunk_count, sizeof(Chunk *));

  for (size_t i = 0; i < chunk_count; i++) {
    load_chunk(i, program);
  }
}

void load_chunk(size_t chunk_idx, program_bytes_t *program) {
  vm.chunks[chunk_idx] = calloc(1, sizeof(Chunk));
  Chunk *chunk = vm.chunks[chunk_idx];
  chunk_init(chunk);

  load_constants(&chunk->constants, program, &vm.strings);
  uint8_t locals_count = 0;
  PROG_CPY(locals_count, program, uint8_t);
  chunk->local_count = locals_count;

  uint32_t ops_count = 0;
  PROG_CPY(ops_count, program, uint32_t);
  uint32_t ops_length = 0;
  PROG_CPY(ops_length, program, uint32_t);
  chunk->code = program->bytes;
  DEBUG_PRINT("chunk count is %d\n", ops_count);
  chunk->count = ops_count;
  program->bytes += ops_length;
  program->count -= ops_length;

  chunk->lines = (uint16_t *)program->bytes;
  program->bytes += ops_count * sizeof(uint16_t);
  program->count -= ops_count * sizeof(uint16_t);

  // for (size_t i = 0; i < ops_count; i++) {
  //     PROG_CPY(line, program, uint16_t);
  //     if(!system_is_little_endian) line = REV_U16(line);
  //     load_op(vm, chunk_idx, line, program);
  // }
}

void load_constants(ValueArray *array, program_bytes_t *program,
                    Table *strings) {
  // 1 byte: the number of constants
  uint8_t constants_count = 0;
  PROG_CPY(constants_count, program, uint8_t);
  for (size_t i = 0; i < constants_count; i++) {
    // 1 byte: the ValueType
    uint8_t type_byte = 0;
    PROG_CPY(type_byte, program, uint8_t);
    ValueType type = (ValueType)type_byte;

    Value constant = {.type = type, .as.integer = 0};
    switch (type) {
    case TYPE_LONG:
      // 8 bytes: the int64 value
      PROG_CPY(constant.as.integer, program, int64_t);
      if (!system_is_little_endian) {
        constant.as.integer = REV_U64(constant.as.integer);
      }
      break;
    case TYPE_DOUBLE:
      // 8 bytes: the float value
      prog_read_bytes(&(constant.as.fp), program, sizeof(double), 1);
      if (!system_is_little_endian) {
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

      if (((ObjectType)obj_type) == OBJ_STRING) {
        char buff[STRING_STACK_BUFF_LEN];
        char *string = buff;
        // TODO: lower, have to make REV for that size
        //  8 bytes: string length
        uint64_t string_length = 0;
        PROG_CPY(string_length, program, int64_t);
        if (!system_is_little_endian) {
          string_length = REV_U64(string_length);
        }
        if (string_length > STRING_STACK_BUFF_LEN) {
          string = calloc(string_length + 1, sizeof(char));
          if (string == NULL) {
            fprintf(stderr,
                    "error: couldn't allocate to read program string\n");
            exit(1);
          }
        }

        prog_read_bytes(string, program, sizeof(char), string_length);
        ObjectString *const_pool_string =
            object_string_allocate(strings, string, string_length);
        constant.type = TYPE_OBJ;
        constant.as.object = (Obj *)const_pool_string;
        if (string_length > STRING_STACK_BUFF_LEN) {
          free(string);
        }
      } else {
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
void load_op(size_t chunk_idx, uint16_t line, program_bytes_t *program) {
  // OpCode opcode = 0;
  // PROG_CPY(opcode, program, uint8_t);
  // Chunk *chunk = vm.chunks[chunk_idx];
  // switch (opcode) {
  //     case OP_DCONST:
  //     case OP_CALL:
  //     case OP_CALL_NATIVE:
  //     case OP_STRCONST:
  //     case OP_LFUNC:
  //     case OP_LCONST:
  //     case OP_DEFGLOBAL:
  //     case OP_GETGLOBAL:
  //     case OP_SETGLOBAL:
  //     case OP_BLOCK:
  //     case OP_DEFLOCAL:
  //     case OP_GETLOCAL:
  //     case OP_SETLOCAL:
  //         CHUNK_WRITE(uint8_t, opcode, line);
  //         uint8_t u8_arg = 0;
  //         PROG_CPY(u8_arg, program, uint8_t);
  //         CHUNK_WRITE(uint8_t, u8_arg, line);
  //         break;
  //     case OP_JUMP:
  //     case OP_LOOP:
  //     case OP_JUMP_IF_FALSE:
  //     case OP_JUMP_IF_TRUE:
  //         CHUNK_WRITE(uint8_t, opcode, line);
  //         uint16_t offset = 0;
  //         PROG_CPY(offset, program, uint16_t);
  //         CHUNK_WRITE(uint16_t, offset, line);
  //         break;
  //     default:
  //         CHUNK_WRITE(uint8_t, opcode, line);
  //         break;
  // }
}
