#if !defined(uza_vm_h)
#define uza_vm_h

#include "common.h"
#include "stdio.h"
#include "chunk.h"

#define STACK_MAX (1048576 / sizeof(Value)) // 1MiB

typedef struct {
    // uint8_t version[3];
    Chunk chunk;
    uint8_t* ip;
    Value stack[STACK_MAX];
    Value* stack_top;
} VM;

#define STACK_IS_EMPTY(vm) (vm->stack_top == vm->stack)


void  push(VM* vm, Value value);
Value pop(VM* vm);

VM*  vm_init(program_bytes_t* program);
void vm_stack_reset(VM* vm);
void vm_free(VM* vm);

void interpret(VM* vm);

#endif // uza_vm_h
