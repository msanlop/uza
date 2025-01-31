#ifndef uza_debug_h
#define uza_debug_h

#include "chunk.h"
#include "common.h"
#include "vm.h"

int debug_op_print(Chunk *chunk, int offset);
void debug_constant_print(char *code_str, Chunk *chunk, int offset);
void debug_chunk_print(Chunk *chunk);
void debug_vm_dump(void);
void debug_stack_print(char *str);
void debug_locals_print(char *str);
void debug_value_array_print(ValueArray *array);

#endif // uza_debug_h
