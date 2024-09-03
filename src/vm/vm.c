#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "chunk.h"
#include "common.h"
#include "serializer.h"
#include "vm.h"
#include "memory.h"
#include "value.h"

#ifdef DEBUG
#include "debug.h"
#endif

#define PEEK(vm) (*(vm->stack_top - 1))

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
            printf("\n");
            // DEBUG_PRINT("----------\n");

        #endif // #define DEBUG_TRACE_EXECUTION_OP
        OpCode instruction = *vm->ip++;
        switch (instruction)
        {
        case OP_RETURN:
            // simulate print() to test code, TODO: remove when obsolete
            PRINT_VALUE((*(vm->stack_top-1))); 
            return;
        case OP_STRCONST:
        case OP_DCONST:
        case OP_LCONST: push(vm, vm->chunk.constants.values[*(vm->ip++)]); 
            break;
        case OP_ADD: {
            Value top = PEEK(vm);
            if (IS_STRING(top)) {
                Value rhs = pop(vm);
                Value lhs = pop(vm);
                ObjectString* lhs_string = AS_STRING(lhs);
                int new_len = lhs_string->length + AS_STRING(rhs)->length;
                ObjectString* new_object_string = object_string_allocate(new_len);
                memcpy(new_object_string->chars, lhs_string->chars, lhs_string->length);
                strlcat(
                    new_object_string->chars,
                    AS_STRING(rhs)->chars,
                    new_len + 1
                );
                new_object_string->length = new_len;
                new_object_string->obj.type = OBJ_STRING;
                Value new_object_value = {
                    .type=TYPE_OBJ, 
                    .as.object=(Obj*) new_object_string
                };
                // new_chars->length = new_size;
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
