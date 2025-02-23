#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "chunk.h"
#include "common.h"
#include "memory.h"
#include "native.h"
#include "serialize.h"
#include "value.h"
#include "vm.h"

#ifndef NDEBUG
#include "debug.h"
#endif

#define SET_STACK_VALUE_TO_BOOL (vm.stack_top[-1].type = TYPE_BOOL)

#define GET_FRAME(up_count) (&vm.frame_stacks[vm.depth - up_count])

#define IP_FETCH_INCR (*(frame->ip++))
#define CURR_FRAME ()

#define CONSTANT(constant_offset) (chunk->constants.values[constant_offset])

#define BINARY_OP(op)                                                          \
  do {                                                                         \
    Value rhs = pop();                                                         \
    Value lhs = pop();                                                         \
    if (IS_DOUBLE(lhs) || IS_DOUBLE(rhs)) {                                    \
      if (IS_INTEGER(lhs)) {                                                   \
        I2D(lhs);                                                              \
      } else if (IS_INTEGER(rhs)) {                                            \
        I2D(rhs);                                                              \
      }                                                                        \
      (lhs).as.fp = (lhs).as.fp op(rhs).as.fp;                                 \
    } else {                                                                   \
      (lhs).as.integer = (lhs).as.integer op(rhs).as.integer;                  \
    }                                                                          \
    push(lhs);                                                                 \
  } while (false);

#define JUMP_IF(value)                                                         \
  do {                                                                         \
    if (value) {                                                               \
      int offset = ((uint16_t)*(frame->ip)) + sizeof(uint16_t);                \
      frame->ip += offset;                                                     \
    } else {                                                                   \
      frame->ip += sizeof(uint16_t);                                           \
    }                                                                          \
  } while (0);

extern bool stop_interpreting;
VM vm = {0};
bool enable_garbage_collection = false;

inline void vm_stack_reset(void) { stack_top_set(vm.stack); }

void vm_init(program_bytes_t *program) {
  vm = (VM){0};
  vm.nextGC = 1024 * 1024;
  enable_garbage_collection = false;

  initTable(&vm.strings);
  initTable(&vm.globals);
  read_program(program);

  size_t count;
  const NativeFunction *natives = native_functions_get(&count);
  for (size_t i = 0; i < count; i++) {
    const NativeFunction *func = &natives[i];
    ObjectString *func_name =
        object_string_allocate(&vm.strings, func->name, func->name_len);
    ObjectFunction *func_obj = object_function_allocate();
    func_obj->arity = func->arity;
    func_obj->function = func->function;
    func_obj->obj = (Obj){OBJ_FUNCTION_NATIVE, NULL};
    func_obj->name = func_name;
    tableSet(&vm.globals, func_name, VAL_OBJ(func_obj));
  }

  vm.depth = 0;
  Frame *global_frame = &vm.frame_stacks[vm.depth];
  global_frame->function = object_function_allocate();
  global_frame->function->chunk = vm.chunks[0];
  global_frame->function->name =
      object_string_allocate(&vm.strings, "__global__", sizeof("__global__"));
  global_frame->ip = global_frame->function->chunk->code;
  global_frame->locals_count = global_frame->function->chunk->local_count;
  global_frame->is_block = false;
  global_frame->locals = vm.stack;

  vm_stack_reset();
  stack_top_set(vm.stack_top + global_frame->locals_count);
}

void vm_free(void) {
  freeTable(&vm.strings);
  freeTable(&vm.globals);
  // chunk_free(vm.chunks);
  if (vm.gray_stack)
    free(vm.gray_stack);
}

int interpret(void) {
  enable_garbage_collection = true;

  // update these two when calling/returning
  Frame *frame = &vm.frame_stacks[vm.depth];
  Chunk *chunk = frame->function->chunk;

  while (!stop_interpreting) {

#ifdef DEBUG_TRACE_EXECUTION_OP
    DEBUG_PRINT(PURPLE "running op\n  " RESET);
    debug_op_print(chunk, (int)(frame->ip - chunk->code));
    fprintf(stderr, "\n");
    // DEBUG_PRINT("----------\n");

#endif // #define DEBUG_TRACE_EXECUTION_OP
#ifdef DEBUG_TRACE_EXECUTION_STACK
    debug_locals_print("locals");
    debug_stack_print("before");
#endif // #define DEBUG_TRACE_EXECUTION_STACK

    OpCode instruction = IP_FETCH_INCR;

    switch (instruction) {
    case OP_RETURN: {
      Value ret_val = PEEK_AT(0);
      Value *old_stack_top = vm.stack_top;
      Value *old_locals = GET_FRAME(0)->locals;
      stack_top_set(GET_FRAME(0)->locals);
      assert(old_stack_top >= vm.stack_top);
      vm.depth--;
      frame = GET_FRAME(0);
      chunk = frame->function->chunk;

      assert(vm.stack_top >= &frame->locals[frame->locals_count]);
      push(ret_val);
    } break;
    case OP_CALL: {
      Value *func_name = &PEEK(vm);
      ObjectFunction *func;

      if (IS_STRING(*func_name)) {
        ObjectFunction *func_obj = AS_STRING(*func_name)->cached_function;
        if (func_obj != NULL) {
          func = func_obj;
        } else {
          Value func_val = VAL_NIL;
          if (!tableGet(&vm.globals, AS_STRING(*func_name), &func_val)) {
            PRINT_ERR("Could not find function: ");
            PRINT_VALUE(*func_name, stderr);
            fprintf(stderr, NEWLINE);
            exit(1);
          }

          func_obj = AS_FUNCTION(func_val);
          AS_STRING(*func_name)->cached_function = func_obj;
          func = func_obj;
        }
      }
      pop();
      vm.depth++;
      Frame *curr = GET_FRAME(0);
      frame = curr;
      curr->function = func;
      chunk = frame->function->chunk;
      curr->locals_count = func->chunk->local_count;
      curr->locals = vm.stack_top - func->arity; // args are in the stack
      curr->ip = func->chunk->code;
      curr->is_block = false;
      stack_top_set(&curr->locals[curr->locals_count]);

      chunk = func->chunk;

#ifndef NDEBUG
      // set non initialized local to NIL
      for (Value *local = curr->locals + func->arity; local != vm.stack_top;
           local += 1) {
        *local = VAL_NIL;
      }
#endif
      assert(vm.stack_top >= &curr->locals[curr->locals_count]);
    }; break;
    case OP_CALL_NATIVE: {
      uint8_t offset = IP_FETCH_INCR;
      Value *func_ptr = &(CONSTANT(offset));

      if (IS_STRING(*func_ptr)) {
        ObjectFunction *func_obj = AS_STRING(*func_ptr)->cached_function;
        if (func_obj != NULL) {
          func_obj->function();
        } else {
          Value func_val = VAL_NIL;
          if (!tableGet(&vm.globals, AS_STRING(*func_ptr), &func_val)) {
            PRINT_ERR("Could not find function: ");
            PRINT_VALUE(*func_ptr, stderr);
            fprintf(stderr, NEWLINE);
            exit(1);
          }

          func_obj = AS_FUNCTION(func_val);
          AS_STRING(*func_ptr)->cached_function = func_obj;
          func_obj->function();
        }
      }
    } break;
    case OP_JUMP: {
      int offset = ((uint16_t)*(frame->ip)) + sizeof(uint16_t);
      frame->ip += offset;
    } break;
    case OP_LOOP: {
      int offset = ((uint16_t)*(frame->ip)) + 1;
      frame->ip -= offset;
    } break;
    case OP_POP:
      pop();
      break;
    case OP_LFUNC: {
      Value idx = CONSTANT(IP_FETCH_INCR);
      pop(); // unused local_count, update lfunc call
      Value arity = pop();
      ObjectFunction *func = object_function_allocate();
      func->chunk = vm.chunks[idx.as.integer];
      func->chunk->local_count = func->chunk->local_count;
      func->name = AS_STRING(pop());
      func->arity = arity.as.integer;
      push(VAL_OBJ(func)); // avoid free(func)
      tableSet(&vm.globals, func->name,
               (Value){TYPE_OBJ, .as.object = (Obj *)func});
      pop();
    } break;
    case OP_LNIL: {
      push(VAL_NIL);
    } break;
    case OP_STRCONST:
    case OP_DCONST:
    case OP_LCONST:
      push(CONSTANT(IP_FETCH_INCR));
      break;
    case OP_BOOLTRUE:
      push(VAL_BOOL(true));
      break;
    case OP_BOOLFALSE:
      push(VAL_BOOL(false));
      break;
    case OP_JUMP_IF_FALSE: {
      Value val = PEEK(vm);
      JUMP_IF(!val.as.boolean);
    } break;
    case OP_JUMP_IF_TRUE: {
      Value val = PEEK(vm);
      JUMP_IF(val.as.boolean);
    } break;
    case OP_ADD: {
      Value top = PEEK(vm);
      if (IS_STRING(top)) {
        Value rhs = pop();
        Value lhs = pop();
        ObjectString *new_object_string =
            object_string_concat(&vm.strings, AS_STRING(lhs), AS_STRING(rhs));
        Value new_object_value = {.type = TYPE_OBJ,
                                  .as.object = (Obj *)new_object_string};
        push(new_object_value);
      } else {
        BINARY_OP(+);
      }
    } break;
    case OP_SUB: {
      BINARY_OP(-);
    } break;
    case OP_MUL: {
      BINARY_OP(*);
    } break;
    case OP_DIV: {
      BINARY_OP(/);
    } break;
    case OP_MOD: {
      Value rhs = pop();
      Value lhs = pop();
      int64_t res = (lhs).as.integer % (rhs).as.integer;
      push(VAL_INT(res));
    } break;
    case OP_NEG: {
      Value *val = &PEEK(vm);
      if (val->type == TYPE_DOUBLE) {
        val->as.fp = -val->as.fp;
      } else if (val->type == TYPE_LONG) {
        val->as.integer = -val->as.integer;
      } else {
        PRINT_ERR_ARGS("at %s:%d cannot neg type : %d\n\n", __FILE__, __LINE__,
                       val->type);
        return 1;
      }
    } break;
    case OP_EQ: {
      BINARY_OP(==);
      SET_STACK_VALUE_TO_BOOL;
    } break;
    case OP_NE: {
      BINARY_OP(!=);
      SET_STACK_VALUE_TO_BOOL;
    } break;
    case OP_LT: {
      BINARY_OP(<);
      SET_STACK_VALUE_TO_BOOL;
    } break;
    case OP_LE: {
      BINARY_OP(<=);
      SET_STACK_VALUE_TO_BOOL;
    } break;
    case OP_GT: {
      BINARY_OP(>);
      SET_STACK_VALUE_TO_BOOL;
    } break;
    case OP_GE: {
      BINARY_OP(>=);
      SET_STACK_VALUE_TO_BOOL;
    } break;
    case OP_NOT: {
      PEEK(vm).as.boolean = !PEEK(vm).as.boolean;
      PEEK(vm).type = TYPE_BOOL;
      SET_STACK_VALUE_TO_BOOL;
    } break;
    case OP_TOSTRING: {
      if (IS_STRING(PEEK(vm))) {
        break;
      }

      Value val = pop();
      ObjectString *res;
      char buff[512] = {0};
      if (IS_INTEGER(val)) {
        int char_count = sprintf(buff, "%lld", val.as.integer);
        res = object_string_allocate(&vm.strings, buff, char_count);
      } else if (IS_DOUBLE(val)) {
        int char_count = sprintf(buff, "%lf", val.as.fp);
        res = object_string_allocate(&vm.strings, buff, char_count);
      } else {
        PRINT_ERR_ARGS("ERROR: Invalid invalid type conversion for type %d\n",
                       val.type);
      }

      push(VAL_OBJ(res));
    } break;
    case OP_TOFLOAT: {
      if (IS_DOUBLE(PEEK(vm))) {
        break;
      }
      if (IS_STRING(PEEK(vm))) {
        PRINT_ERR_ARGS("at %s:%d not implemented string to float : %d\n\n",
                       __FILE__, __LINE__, instruction);
        return 1;
      }

      Value *val = &PEEK(vm);
      if (IS_INTEGER(*val)) {
        val->as.fp = (double)val->as.integer;
        val->type = TYPE_DOUBLE;
      }
    } break;
    case OP_TOINT: {
      if (IS_INTEGER(PEEK(vm))) {
        break;
      }
      if (IS_STRING(PEEK(vm))) {
        int64_t num = atoll(AS_STRING(pop())->chars);
        push(VAL_INT(num));
      }

      Value *val = &PEEK(vm);
      if (IS_DOUBLE(*val)) {
        val->as.integer = (int64_t)val->as.fp;
        val->type = TYPE_LONG;
      }
    } break;
    case OP_DEFGLOBAL: {
      int constant = IP_FETCH_INCR;
      ObjectString *identifier = AS_STRING(CONSTANT(constant));
      tableSet(&vm.globals, identifier, PEEK(vm));
      pop();
    } break;
    case OP_GETGLOBAL: {
      int constant = IP_FETCH_INCR;
      ObjectString *identifier = AS_STRING(CONSTANT(constant));
      Value val = {0};
      tableGet(&vm.globals, identifier, &val);
      push(val);
    } break;
    case OP_SETGLOBAL: {
      int constant = IP_FETCH_INCR;
      ObjectString *identifier = AS_STRING(CONSTANT(constant));
      Value val = PEEK(vm);
      tableSet(&vm.globals, identifier, val);
      pop();
    } break;
    case OP_DEFLOCAL: {
      Value val = pop();
      frame->locals[IP_FETCH_INCR] = val;
    } break;
    case OP_GETLOCAL: {
      push(frame->locals[IP_FETCH_INCR]);
    } break;
    case OP_SETLOCAL: {
      frame->locals[IP_FETCH_INCR] = pop();
    } break;
    case OP_EXITVM:
      return 0;
    default: {
      PRINT_ERR_ARGS("at %s:%d unknown instruction : %d\n\n", __FILE__,
                     __LINE__, instruction);
      exit(1);
    } break;
    }
#ifdef DEBUG_TRACE_EXECUTION_STACK
    debug_stack_print("after");
#endif // #define DEBUG_TRACE_EXECUTION_STACK
  }
  return 1;
}

#undef BINARY_OP
