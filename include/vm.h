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
    Obj *objects;
    Chunk **chunks;
    size_t chunk_count;
    Value stack[STACK_MAX];
    Value* stack_top;
    uint16_t depth;
    // TODO: see about type, so far only hold locals
    Frame frame_stacks[FRAMES_MAX]; // points to the spot after last local
    Table strings;
    Table globals;
    int gray_count;
    int gray_capacity;
    Obj** gray_stack;
} VM;


extern VM vm;
extern bool enable_garbage_collection;

void  push(Value value);
Value peek();
Value pop();

void vm_init(program_bytes_t* program);
void vm_stack_reset();
void vm_free();

int interpret();

#endif // uza_vm_h
