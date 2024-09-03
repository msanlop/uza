#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "chunk.h"
#include "common.h"
#include "serializer.h"
#include "vm.h"
#include "memory.h"
#include "value.h"

#ifdef DEBUG
#include "debug.h"
#endif

#define BINARY_OP(vm, op) \
    do { \
        Value lhs = pop(vm); \
        Value rhs = pop(vm); \
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

VM* vm_init(FILE* file) { 
    VM* vm = calloc(1, sizeof(VM));
    if (vm == NULL) return vm;
    read_program(&vm->chunk, file);
    vm->ip = vm->chunk.code;
    vm_stack_reset(vm);
    return vm;
}

void vm_free(VM* vm){
    chunk_free(&vm->chunk);
    free(vm);
}

void interpret(VM* vm) {
    while(true) {
        #ifdef DEBUG_TRACE_EXECUTION_OP
            DEBUG_PRINT(PURPLE "running op\n  " RESET);
            debug_op_print(&vm->chunk, (int) (vm->ip - vm->chunk.code));
            printf("\n");
            // DEBUG_PRINT("----------\n");

        #endif // #define DEBUG_TRACE_EXECUTION_OP

        OpCode instruction = *vm->ip++;
        switch (instruction)
        {
        case OP_RETURN:
            PRINT_VALUE((*(vm->stack_top-1)));
            return;
        case OP_DCONST:
        case OP_LCONST: push(vm, vm->chunk.constants.values[*(vm->ip++)]); 
            break;
        case OP_ADD: {
            BINARY_OP(vm, +);
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
        default: {
            PRINT_ERR_ARGS("unkown instruction : %d\n", instruction);
            exit(1);
            break;
        }
        }
    }
}

#undef BINARY_OP
