#if !defined(uza_vm_h)
#define uza_vm_h

#include "common.h"
#include "object.h"
#include "table.h"
#include "value.h"
#include <stdio.h>
#include "chunk.h"

#define STACK_MAX ((1 << 20) / sizeof(Value)) // 1MiB
#define FRAMES_MAX (1000)

typedef struct {
    ObjectFunction *function;
    size_t locals_count;
    Value *locals;
    uint8_t *ip;
    bool is_block; // _return_ statements pop block frames
} Frame;


typedef struct {
    // uint8_t version[3];
    Chunk **chunks;
    Value stack[STACK_MAX];
    Value* stack_top;
    uint16_t depth;
    // TODO: see about type, so far only hold locals
    Frame frame_stacks[FRAMES_MAX]; // points to the spot after last local
    Table strings;
    Table globals;
} VM;

#define STACK_IS_EMPTY(vm) (vm->stack_top == vm->stack)


void  push(VM* vm, Value value);
Value peek(VM* vm);
Value pop(VM* vm);

VM*  vm_init(program_bytes_t* program);
void vm_stack_reset(VM* vm);
void vm_free(VM* vm);

int interpret(VM* vm);

#endif // uza_vm_h
