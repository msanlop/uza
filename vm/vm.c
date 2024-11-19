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

#ifndef NDEBUG
#include "debug.h"
#endif

#define PEEK(vm) (*(vm->stack_top - 1))

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
            int offset =  ((uint16_t) *(vm->ip)) + sizeof(uint16_t);           \
            vm->ip += offset;                                                  \
        }                                                                      \
        else {                                                                 \
            vm->ip += sizeof(uint16_t);                                        \
        }                                                                      \
    } while (0);



void push(VM* vm, Value value) {
    *vm->stack_top++ = value;
    #ifdef DEBUG_TRACE_EXECUTION_STACK
        DEBUG_PRINT("stack push\n");
    #endif //#define DEBUG_TRACE_EXECUTION_STACK
}

inline Value peek(VM* vm) {
    return vm->stack_top[-1];
}

Value pop(VM* vm) {
    vm->stack_top--;
    #ifdef DEBUG_TRACE_EXECUTION_STACK
        DEBUG_PRINT("stack pop\n");
    #endif //#define DEBUG_TRACE_EXECUTION_STACK
    return *vm->stack_top;
}


void vm_stack_reset(VM* vm) {
    vm->stack_top = vm->stack;
}

VM* vm_init(program_bytes_t* program) {
    VM* vm = calloc(1, sizeof(VM));
    if (vm == NULL) return vm;
    initTable(&vm->strings);
    initTable(&vm->globals);
    read_program(vm, program);
    vm->ip = vm->chunk.code;
    vm->depth = -1;
    vm_stack_reset(vm);
    return vm;
}

void vm_free(VM* vm){
    freeTable(&vm->strings);
    freeTable(&vm->globals);
    chunk_free(&vm->chunk);
    free(vm);
}

int interpret(VM* vm) {

        // char* string = "Hello ";
        // int string_len = strlen(string);
        // ObjectString* new_string = calloc(
        //     1,
        //     sizeof(Obj) + sizeof(int) + string_len + 1
        // );
        // new_string->length = string_len;
        // new_string->obj.type = OBJ_STRING;
        // strlcpy(new_string->chars, string, string_len + 1);
        // push(vm, (Value) {.type=TYPE_OBJ, .as.object=new_string});

        // char* string1 = "world!";
        // int string_len1 = strlen(string1);
        // ObjectString* new_string1 = calloc(
        //     1,
        //     sizeof(Obj) + sizeof(int) + string_len1 + 1
        // );
        // new_string1->length = string_len1;
        // new_string1->obj.type = OBJ_STRING;
        // strlcpy(new_string1->chars, string1, string_len1 + 1);
        // push(vm, (Value) {.type=TYPE_OBJ, .as.object=new_string1});
    while(true) {

        #ifdef DEBUG_TRACE_EXECUTION_OP
            DEBUG_PRINT(PURPLE "running op\n  " RESET);
            debug_op_print(&vm->chunk, (int) (vm->ip - vm->chunk.code));
            fprintf(stderr, "\n");
            // DEBUG_PRINT("----------\n");

        #endif // #define DEBUG_TRACE_EXECUTION_OP
        #ifdef DEBUG_TRACE_EXECUTION_STACK
            debug_stack_print(vm, "before");
        #endif //#define DEBUG_TRACE_EXECUTION_STACK
        OpCode instruction = *vm->ip++;
        switch (instruction) {
        case OP_RETURN: {
            // simulate print() to test code, TODO: remove when obsolete
            Value val = pop(vm);
            DEBUG_PRINT("STDOUT PRINTLN: ");
            PRINT_VALUE(val, stdout);
            printf(NEWLINE);
        }
        break;
        case OP_JUMP: {
            int offset =  ((uint16_t) *(vm->ip)) + sizeof(uint16_t);
            vm->ip += offset;
        }
        break;
        case OP_POP:
            pop(vm);
            break;
        case OP_STRCONST:
        case OP_DCONST:
        case OP_LCONST: push(vm, vm->chunk.constants.values[*(vm->ip++)]);
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
        case OP_DEFGLOBAL: {
            ObjectString *identifier = (ObjectString *) vm->chunk.constants.values[*(vm->ip++)].as.object;
            tableSet(&vm->globals, identifier, pop(vm));
        }
        break;
        case OP_GETGLOBAL: {
            ObjectString *identifier = (ObjectString *) vm->chunk.constants.values[*(vm->ip++)].as.object;
            Value val = {0};
            tableGet(&vm->globals, identifier, &val);
            push(vm, val);
        }
        break;
        case OP_SETGLOBAL: {
            ObjectString *identifier = (ObjectString *) vm->chunk.constants.values[*(vm->ip++)].as.object;
            Value val = pop(vm);
            tableSet(&vm->globals, identifier, val);
        }
        break;
        case OP_BLOCK: {
            vm->depth++;
            Frame *frame = &vm->frame_stacks[vm->depth];
            frame->locals = vm->stack_top;
            int locals_num = *(vm->ip++);

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
            vm->stack_top = vm->frame_stacks[vm->depth].locals;
            vm->depth--;
        }
        break;
        case OP_DEFLOCAL: {
            Value val = pop(vm);
            vm->frame_stacks[vm->depth].locals[*(vm->ip++)] = val;
        }
        break;
        case OP_GETLOCAL: {
            push(vm, vm->frame_stacks[vm->depth].locals[*(vm->ip++)]);
        }
        break;
        case OP_SETLOCAL: {
            vm->frame_stacks[vm->depth].locals[*(vm->ip++)] = pop(vm);
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
