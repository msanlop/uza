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


void push(VM* vm, Value value) {
    *vm->stack_top++ = value;
    #ifdef DEBUG_TRACE_EXECUTION_STACK
        debug_stack_print(vm, "stack: push");
    #endif //#define DEBUG_TRACE_EXECUTION_STACK
}

Value pop(VM* vm) {
    vm->stack_top--;
    #ifdef DEBUG_TRACE_EXECUTION_STACK
        debug_stack_print(vm, "stack: pop");
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
    vm_stack_reset(vm);
    return vm;
}

void vm_free(VM* vm){
    freeTable(&vm->strings);
    freeTable(&vm->globals);
    chunk_free(&vm->chunk);
    free(vm);
}

void interpret(VM* vm) {

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
        OpCode instruction = *vm->ip++;
        switch (instruction)
        {
        case OP_RETURN:
            // simulate print() to test code, TODO: remove when obsolete
            Value val = pop(vm);
            PRINT_VALUE(val, stdout);
            printf(NEWLINE);
            break;
        case OP_STRCONST:
        case OP_DCONST:
        case OP_LCONST: push(vm, vm->chunk.constants.values[*(vm->ip++)]);
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
            break;
        }
        case OP_SUB: {
            BINARY_OP(vm, -);
            break;
        }
        case OP_MUL: {
            BINARY_OP(vm, *);
            break;
        }
        case OP_DIV: {
            BINARY_OP(vm, /);
            break;
        }
        case OP_DEFGLOBAL: {
            ObjectString *identifier = (ObjectString *) vm->chunk.constants.values[*(vm->ip++)].as.object;
            tableSet(&vm->globals, identifier, pop(vm));
            break;
        }
        case OP_GETGLOBAL: {
            ObjectString *identifier = (ObjectString *) vm->chunk.constants.values[*(vm->ip++)].as.object;
            Value val = {0};
            tableGet(&vm->globals, identifier, &val);
            push(vm, val);
            break;
        }
        case OP_SETGLOBAL: {
            ObjectString *identifier = (ObjectString *) vm->chunk.constants.values[*(vm->ip++)].as.object;
            Value val = pop(vm);
            tableSet(&vm->globals, identifier, val);
            break;
        }
        case OP_EXITVM:
            return;
        default: {
            PRINT_ERR_ARGS("at %s:%d unknown instruction : %d\n\n",
                __FILE__, __LINE__, instruction);
            exit(1);
            break;
        }
        }
    }
}

#undef BINARY_OP
