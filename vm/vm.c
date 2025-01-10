#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "common.h"
#include "serializer.h"
#include "vm.h"
#include "memory.h"
#include "value.h"
#include "chunk.h"
#include "native.h"

#ifndef NDEBUG
#include "debug.h"
#endif

#define PEEK(vm) (*(vm->stack_top - 1))

#ifndef NDEBUG
#define DEBUG_SET_STACK_VALUE_TO_BOOL (vm->stack_top[-1].type = TYPE_BOOL)
#else
#define DEBUG_SET_STACK_VALUE_TO_BOOL
#endif

#define GET_FRAME(up_count) (&vm->frame_stacks[vm->depth - up_count])

#define IP_FETCH_INCR (*(frame->ip++))
#define CURR_FRAME ()

#define CONSTANT(constant_offset) (chunk->constants.values[constant_offset])


#define BINARY_OP(vm, op) \
    do { \
        Value rhs = pop(vm); \
        Value lhs = pop(vm); \
        if(IS_DOUBLE(lhs) || IS_DOUBLE(rhs)) { \
            if(IS_INTEGER(lhs)) {I2D(lhs);} \
            else if(IS_INTEGER(rhs)) {I2D(rhs);} \
            (lhs).as.fp = (lhs).as.fp op (rhs).as.fp; \
        } else { \
            (lhs).as.integer = (lhs).as.integer op (rhs).as.integer; \
        } \
        push(vm, lhs); \
    } while (false); \


#define JUMP_IF(value) \
    do {                                                                       \
        if (value) {                                                 \
            int offset =  ((uint16_t) *(frame->ip)) + sizeof(uint16_t);           \
            frame->ip += offset;                                                  \
        }                                                                      \
        else {                                                                 \
            frame->ip += sizeof(uint16_t);                                        \
        }                                                                      \
    } while (0);

extern bool stop_interpreting;

inline void push(VM* vm, Value value) {
    *vm->stack_top++ = value;
    #ifdef DEBUG_TRACE_EXECUTION_STACK
        DEBUG_PRINT("stack push\n");
    #endif //#define DEBUG_TRACE_EXECUTION_STACK
}

inline Value peek(VM* vm) {
    return vm->stack_top[-1];
}

inline Value pop(VM* vm) {
    vm->stack_top--;
    #ifdef DEBUG_TRACE_EXECUTION_STACK
        DEBUG_PRINT("stack pop\n");
    #endif //#define DEBUG_TRACE_EXECUTION_STACK
    return *vm->stack_top;
}


inline void vm_stack_reset(VM* vm) {
    vm->stack_top = vm->stack;
}

VM* vm_init(program_bytes_t* program) {
    VM* vm = calloc(1, sizeof(VM));
    if (vm == NULL) return vm;

    initTable(&vm->strings);
    initTable(&vm->globals);
    read_program(vm, program);

    size_t count;
    const NativeFunction *natives = native_functions_get(&count);
    for (size_t i = 0; i < count; i++)
    {
        const NativeFunction *func = &natives[i];
        ObjectString *func_name = object_string_allocate(&vm->strings, func->name, func->name_len);
        ObjectFunction *func_obj = object_function_allocate();
        func_obj->arity = func->arity;
        func_obj->function = func->function;
        func_obj->obj = (Obj) {OBJ_FUNCTION_NATIVE, NULL};
        func_obj->name = func_name;
        Value test = {TYPE_OBJ, .as.object= (Obj *) func_name};
        Value val = {TYPE_OBJ, .as.object=(Obj *) (func_obj)};
        Value test1 = {0};
        tableSet(&vm->globals, func_name, val);
    }


    vm->depth = 0;
    Frame *global_frame = &vm->frame_stacks[vm->depth];
    global_frame->function = object_function_allocate();
    global_frame->function->chunk = vm->chunks[0];
    global_frame->ip = global_frame->function->chunk->code;
    global_frame->locals_count = 0;
    global_frame->is_block = false;
    global_frame->locals = vm->stack;

    vm_stack_reset(vm);
    return vm;
}

void vm_free(VM* vm){
    freeTable(&vm->strings);
    freeTable(&vm->globals);
    // chunk_free(vm->chunks);
    free(vm);
}

int interpret(VM* vm) {
    while(!stop_interpreting) {

        Frame *frame = &vm->frame_stacks[vm->depth];
        Chunk *chunk = frame->function->chunk;

        #ifdef DEBUG_TRACE_EXECUTION_OP
            DEBUG_PRINT(PURPLE "running op\n  " RESET);
            debug_op_print(chunk, (int) (frame->ip - chunk->code));
            fprintf(stderr, "\n");
            // DEBUG_PRINT("----------\n");

        #endif // #define DEBUG_TRACE_EXECUTION_OP
        #ifdef DEBUG_TRACE_EXECUTION_STACK
            debug_stack_print(vm, "before");
            debug_locals_print(vm, "locals");
        #endif //#define DEBUG_TRACE_EXECUTION_STACK

        OpCode instruction = IP_FETCH_INCR;

        switch (instruction) {
        case OP_RETURN: {
            Value ret_val = pop(vm);
            vm->stack_top = GET_FRAME(0)->locals;
            vm->depth--;
            push(vm, ret_val);
        }
        break;
        case OP_CALL: {
            Value func_name = pop(vm);
            Value func_val = {0};
            tableGet(&vm->globals, AS_STRING(func_name), &func_val);
            ObjectFunction *func = AS_FUNCTION(func_val);
            vm->depth++;
            Frame *curr = GET_FRAME(0);
            frame = curr;
            curr->function = func;
            chunk = frame->function->chunk;

            curr->locals_count = func->arity + chunk->local_count;
            curr->locals = vm->stack_top - func->arity; // args are in the stack
            curr->ip = func->chunk->code;
            curr->is_block = false;
            vm->stack_top = curr->locals + curr->locals_count;
        };
        break;
        case OP_CALL_NATIVE: {
            Value func_val = VAL_NIL;
            Value func_name = CONSTANT(IP_FETCH_INCR);
            if (!tableGet(&vm->globals, AS_STRING(func_name), &func_val)) {
                PRINT_ERR("Could not find function :");
                fprintf(stderr, NEWLINE);
                exit(1);
            }
            ObjectFunction *func = AS_FUNCTION(func_val);
            func->function(vm);
        }
        break;
        case OP_JUMP: {
            int offset =  ((uint16_t) *(frame->ip)) + sizeof(uint16_t);
            frame->ip += offset;
        }
        break;
        case OP_LOOP: {
            int offset =  ((uint16_t) *(frame->ip)) + 1;
            frame->ip -= offset;
        }
        break;
        case OP_POP:
            pop(vm);
            break;
        case OP_LFUNC: {
            Value idx = CONSTANT(IP_FETCH_INCR);
            Value arity = pop(vm);
            Value locals_count = pop(vm);
            ObjectFunction *func = object_function_allocate();
            func->chunk = vm->chunks[idx.as.integer];
            func->chunk->local_count = locals_count.as.integer;
            func->name = AS_STRING(pop(vm));
            func->arity = arity.as.integer;
            tableSet(&vm->globals, func->name, (Value) {TYPE_OBJ, .as.object= (Obj *) func});
        }
        break;
        case OP_STRCONST:
        case OP_DCONST:
        case OP_LCONST: push(vm, CONSTANT(IP_FETCH_INCR));
            break;
        case OP_BOOLTRUE:
            push(vm, VAL_BOOL(true));
            break;
        case OP_BOOLFALSE:
            push(vm, VAL_BOOL(false));
            break;
        case OP_JUMP_IF_FALSE: {
            Value val = peek(vm);
            JUMP_IF(!val.as.boolean);
        }
        break;
        case OP_JUMP_IF_TRUE: {
            Value val = peek(vm);
            JUMP_IF(val.as.boolean);
        }
        break;
        case OP_ADD: {
            Value top = PEEK(vm);
            if (IS_STRING(top)) {
                Value rhs = pop(vm);
                Value lhs = pop(vm);
                ObjectString *new_object_string = object_string_concat(&vm->strings, AS_STRING(lhs), AS_STRING(rhs));
                Value new_object_value = {
                    .type=TYPE_OBJ,
                    .as.object=(Obj*) new_object_string
                };
                push(vm, new_object_value);
            }
            else {
                BINARY_OP(vm, +);
            }
        }
        break;
        case OP_SUB: {
            BINARY_OP(vm, -);
        }
        break;
        case OP_MUL: {
            BINARY_OP(vm, *);
        }
        break;
        case OP_DIV: {
            BINARY_OP(vm, /);
        }
        break;
        case OP_EQ: {
            BINARY_OP(vm, ==);
            DEBUG_SET_STACK_VALUE_TO_BOOL;
        }
        break;
        case OP_LT: {
            BINARY_OP(vm, <);
            DEBUG_SET_STACK_VALUE_TO_BOOL;
        }
        break;
        case OP_DEFGLOBAL: {
            int constant = IP_FETCH_INCR;
            ObjectString *identifier = AS_STRING(CONSTANT(constant));
            tableSet(&vm->globals, identifier, pop(vm));
        }
        break;
        case OP_GETGLOBAL: {
            int constant = IP_FETCH_INCR;
            ObjectString *identifier = AS_STRING(CONSTANT(constant));
            Value val = {0};
            tableGet(&vm->globals, identifier, &val);
            push(vm, val);
        }
        break;
        case OP_SETGLOBAL: {
        int constant = IP_FETCH_INCR;
        ObjectString *identifier = AS_STRING(CONSTANT(constant));
        Value val = pop(vm);
        tableSet(&vm->globals, identifier, val);
        }
        break;
        case OP_BLOCK: {
            vm->depth++;
            frame = GET_FRAME(0);
            frame->function = GET_FRAME(1)->function;
            frame->ip = GET_FRAME(1)->ip;
            frame->locals = vm->stack_top;
            int locals_num = IP_FETCH_INCR;
            frame->locals_count = locals_num;

            #ifndef NDEBUG
            for (size_t i = 0; i < locals_num; i++) {
                push(vm, VAL_NIL);
                frame->locals[i] = VAL_NIL;
            }
            #endif

            vm->stack_top = frame->locals + locals_num;
        }
        break;
        case OP_EXITBLOCK: {
            uint8_t *curr_ip = frame->ip;
            vm->stack_top = frame->locals;
            vm->depth--;
            frame = &vm->frame_stacks[vm->depth];
            frame->ip = curr_ip;
        }
        break;
        case OP_DEFLOCAL: {
            Value val = pop(vm);
            frame->locals[IP_FETCH_INCR] = val;
        }
        break;
        case OP_GETLOCAL: {
            push(vm, frame->locals[IP_FETCH_INCR]);
        }
        break;
        case OP_SETLOCAL: {
            frame->locals[IP_FETCH_INCR] = pop(vm);
        }
        break;
        case OP_EXITVM:
            return 0;
        default: {
            PRINT_ERR_ARGS("at %s:%d unknown instruction : %d\n\n",
                __FILE__, __LINE__, instruction);
            return 1;
        }
        break;
        }
        #ifdef DEBUG_TRACE_EXECUTION_STACK
            debug_stack_print(vm, "after");
        #endif //#define DEBUG_TRACE_EXECUTION_STACK
    }
    return 1;
}

#undef BINARY_OP
