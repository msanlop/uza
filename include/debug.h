#ifndef uza_debug_h
#define uza_debug_h

#include "common.h"
#include "chunk.h"
#include "vm.h"

int  debug_op_print(Chunk* chunk, int offset);
void debug_constant_print(char* code_str, Chunk* chunk, int offset);
void debug_chunk_print(Chunk* chunk);
void debug_vm_dump(VM* vm);
void debug_stack_print(VM* vm, char* str);
void debug_value_array_print(ValueArray* array);


#endif // uza_debug_h
