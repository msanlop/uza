#include <math.h>
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


void push(VM* vm, Value value) {
    *vm->stack_top++ = value;
    #ifdef DEBUG_TRACE_EXECUTION_STACK
        debug_stack_print(vm, "stack: pushed");
    #endif //#define DEBUG_TRACE_EXECUTION_STACK
}

Value pop(VM* vm) {
    vm->stack_top--;
    #ifdef DEBUG_TRACE_EXECUTION_STACK
        debug_stack_print(vm, "stack: popped");
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
        OpCode instruction = *vm->ip++;
        
        #ifdef DEBUG_TRACE_EXECUTION_OP
            DEBUG_PRINT("running op\n");
            debug_op_print(&vm->chunk, (int) (vm->ip - 1 - vm->chunk.code));
            printf("\n");
            DEBUG_PRINT("----------\n");

        #endif // #define DEBUG_TRACE_EXECUTION_OP

        switch (instruction)
        {
        case OP_RETURN:
            return;
        case OP_LOAD_CONST: {
            push(vm, vm->chunk.constants.values[*vm->ip++]);
            break;
        }
        case OP_ADD: {
            Value rhs = pop(vm);
            Value* overwrite = vm->stack_top - 1;
            Value lhs = *overwrite;
            *overwrite = lhs + rhs;
            break; 
        }
        case OP_SUB: {
            Value rhs = pop(vm);
            Value* overwrite = vm->stack_top - 1;
            Value lhs = *overwrite;
            *overwrite = lhs - rhs;
            break; 
        }
        case OP_MUL: {
            Value rhs = pop(vm);
            Value* overwrite = vm->stack_top - 1;
            Value lhs = *overwrite;
            *overwrite = lhs * rhs;
            break; 
        }
        case OP_DIV: {
            Value rhs = pop(vm);
            Value* overwrite = vm->stack_top - 1;
            Value lhs = *overwrite;
            *overwrite = lhs / rhs;
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