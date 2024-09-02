#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "chunk.h"
#include "common.h"
#include "serializer.h"
#include "vm.h"
#include "memory.h"
#include "value.h"



void read_program_version(uint8_t* buff, FILE* file) {
    fread(buff, sizeof(uint8_t), 3, file);
}

void read_program(Chunk* chunk, FILE* file) {

    uint8_t version[3] = {0};
    read_program_version(version, file);
    load_chunk(chunk, file);
}

void push(VM* vm, Value value) {
    *vm->stack_top++ = value;
    #ifdef DEBUG_TRACE_EXECUTION_STACK
        if(STACK_IS_EMPTY(vm)) {
            DEBUG_PRINT("stack after push is empty\n");
        }
        else {
            DEBUG_PRINT("stack after push \n");
            for (Value* slot = vm->stack; slot < vm->stack_top; slot++) {
                printf(YELLOW " %f\n" RESET, *slot);
            }
        }
    #endif //#define DEBUG_TRACE_EXECUTION_STACK
}

Value pop(VM* vm) {
    vm->stack_top--;
    #ifdef DEBUG_TRACE_EXECUTION_STACK
        if(STACK_IS_EMPTY(vm)) {
            DEBUG_PRINT("stack after pop is empty\n");
        }
        else {
            DEBUG_PRINT("stack after pop \n");
            for (Value* slot = vm->stack; slot < vm->stack_top; slot++) {
                printf(YELLOW " %f\n" RESET, *slot);
            }
        }
    #endif //#define DEBUG_TRACE_EXECUTION_STACK
    return *vm->stack_top;
}

void print_stack(VM* vm) {
    Value* stack_curr = vm->stack;
    while(stack_curr != vm->stack_top) {
        printf("  %f\n", *stack_curr);
        stack_curr++;
    }
}

void reset_stack(VM* vm) {
    vm->stack_top = vm->stack;
}

VM* init_vm(FILE* file) { 
    VM* vm = calloc(1, sizeof(VM));
    if (vm == NULL) return vm;
    read_program(&vm->chunk, file);
    vm->ip = vm->chunk.code;
    reset_stack(vm);
    return vm;
}

void dump_vm(VM* vm) { 
    printf("///  VM   ///\n");
    printf("ip: %p\n", vm->ip);
    printf("/// stack ///\n");
    printf("count: %d\n", (int) (vm->stack_top - vm->stack));
    printf("values:\n");
    print_stack(vm);
    print_chunk(&vm->chunk);
    printf("/////////////\n");
}

void free_vm(VM* vm){
    free_chunk(&vm->chunk);
    free(vm);
}

void interpret(VM* vm) {
    while(true) {
        OpCode instruction = *vm->ip++;
        
        #ifdef DEBUG_TRACE_EXECUTION_OP
            DEBUG_PRINT(" running op ");
            print_opcode(&vm->chunk, (int) (vm->ip - 1 - vm->chunk.code));
            printf("\n");
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
            PRINT_ERR("UNKNOWN INSTRUCTION FOUND");
            return;
            break;
        }
        }
    }
}