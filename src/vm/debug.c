#include "debug.h"
#include "common.h"

#ifdef DEBUG

void debug_stack_print(VM* vm, char* str) {
    if(STACK_IS_EMPTY(vm)) {
        DEBUG_PRINT("stack after push is empty\n");
    }
    else {
        DEBUG_PRINT("%s\n", str);
        for (Value* slot = vm->stack; slot < vm->stack_top; slot++) {
            printf(YELLOW " %f\n" RESET, *slot);
        }
    }
    DEBUG_PRINT("----------\n");

}

void debug_constant_print(char* code_str, Chunk* chunk, int offset){
    printf("%s    ", code_str);
    int constant = GET_CODE_AT(chunk, offset);
    Value val = chunk->constants.values[constant];
    printf("'%.3lf'", val);
}

int debug_op_print(Chunk* chunk, int offset) {
    printf("%04d  ", offset);
    uint16_t line = GET_LINE_AT(chunk, offset);
    if(offset>0 && GET_LINE_AT(chunk, offset-1) == line) {
        printf("    |  ");
    } else {
        printf("%5d  ", line);
    }
    
    switch (GET_CODE_AT(chunk, offset))
    {
    case OP_RETURN:
        printf("OP_RETURN");
        return 1;
        break;
    case OP_LOAD_CONST:
        debug_constant_print("OP_LOAD_CONST", chunk, offset + 1);
        return 2;
        break;
    case OP_ADD:
        printf("OP_ADD");
        return 1;
        break;
    case OP_SUB:
        printf("OP_SUB");
        return 1;
    case OP_MUL:
        printf("OP_MUL");
        return 1;
    case OP_DIV:
        printf("OP_DIV");
        return 1;
        break;
    default:
        break;
    }
    PRINT_ERR_ARGS("OP CODE NOT FOUND %d", GET_CODE_AT(chunk, offset));
    exit(1);
}

void debug_chunk_print(Chunk* chunk) {
    printf("/// Chunk ///\n");
    for (size_t offset = 0; offset < chunk->count;)
    {
        int incr = debug_op_print(chunk, offset);
        offset+=incr;
        printf("\n");
    }
 }

void debug_vm_dump(VM* vm) {
    printf("///  VM   ///\n");
    printf("ip: %p\n", vm->ip);
    printf("/// stack ///\n");
    printf("count: %d\n", (int) (vm->stack_top - vm->stack));
    debug_stack_print(vm, "values:");
    debug_chunk_print(&vm->chunk);
    printf("/////////////\n");
}

#endif
