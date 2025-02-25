#if !defined(uza_vm_h)
#define uza_vm_h

#include "chunk.h"
#include "common.h"
#include "object.h"
#include "table.h"
#include "value.h"
#include <stdio.h>

#define STACK_MAX ((1 << 22) / sizeof(Value)) // 4MiB
#define FRAMES_MAX (1000)

#define CHECK_STACK_OVERFLOW                                                   \
  do {                                                                         \
    if (vm.stack_top >= &vm.stack[STACK_MAX]) {                                \
      PRINT_ERR("Stack overflow!\nexiting...\n");                              \
      exit(1);                                                                 \
    }                                                                          \
  } while (0)

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
  Value *stack_top;
  uint16_t depth;
  // TODO: see about type, so far only hold locals
  Frame frame_stacks[FRAMES_MAX]; // points to the spot after last local
  Table strings;
  Table globals;
  int gray_count;
  int gray_capacity;
  Obj **gray_stack;
  size_t bytesAllocated;
  size_t nextGC;
} VM;

#define PEEK(vm) (*(vm.stack_top - 1))
#define PEEK_AT(spot) (*(vm.stack_top - 1 - spot))
#define POP_COUNT(n)                                                           \
  do {                                                                         \
    for (size_t i = 0; i < n; i++) {                                           \
      pop();                                                                   \
    }                                                                          \
  } while (0);

extern VM vm;
extern bool enable_garbage_collection;

static inline
#if defined(MSVC)
    __forceinline
#elif defined(CLANG) || defined(GNU)
    __attribute__((always_inline))
#endif
    void
    push(Value value) {
  *vm.stack_top++ = value;
  CHECK_STACK_OVERFLOW;
#ifdef DEBUG_TRACE_EXECUTION_STACK
  DEBUG_PRINT("stack push\n");
#endif // #define DEBUG_TRACE_EXECUTION_STACK
}

static inline
#if defined(MSVC)
    __forceinline
#elif defined(CLANG) || defined(GNU)
    __attribute__((always_inline))
#endif
    void
    stack_top_set(Value *new_stack_top) {
  vm.stack_top = new_stack_top;
  CHECK_STACK_OVERFLOW;
#ifdef DEBUG_TRACE_EXECUTION_STACK
  DEBUG_PRINT("stack push\n");
#endif // #define DEBUG_TRACE_EXECUTION_STACK
}

static inline
#if defined(MSVC)
    __forceinline
#elif defined(CLANG) || defined(GNU)
    __attribute__((always_inline))
#endif
    Value
    pop(void) {
  vm.stack_top--;
#ifdef DEBUG_TRACE_EXECUTION_STACK
  DEBUG_PRINT("stack pop\n");
#endif // #define DEBUG_TRACE_EXECUTION_STACK
  return *vm.stack_top;
}

void vm_init(program_bytes_t *program);
void vm_stack_reset(void);
void vm_free(void);

int interpret(void);

#endif // uza_vm_h
