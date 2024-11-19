#include "debug.h"
#include "common.h"

#ifndef NDEBUG

void debug_stack_print(VM* vm, char* str) {
    if(STACK_IS_EMPTY(vm)) {
        DEBUG_PRINT("%s stack is EMPTY\n", str);
    }
    else {
        DEBUG_PRINT("%s\n" CYAN , str);
        for (Value* slot = vm->stack; slot < vm->stack_top; slot++) {
            PRINT_VALUE((*slot), stderr);
            DEBUG_PRINT("\n")
        }
    }
    DEBUG_PRINT(RESET "----------\n");
}

void debug_local_print(char* code_str, Chunk* chunk, int offset){
    DEBUG_PRINT("%s    ", code_str);
    int local = GET_CODE_AT(chunk, offset);
    DEBUG_PRINT("%3d", local);
}

void debug_constant_print(char* code_str, Chunk* chunk, int offset){
    DEBUG_PRINT("%s    ", code_str);
    int constant = GET_CODE_AT(chunk, offset);
    PRINT_VALUE(chunk->constants.values[constant],stderr);
}

void debug_jump_print(char* code_str, Chunk* chunk, int offset){
    DEBUG_PRINT("%s    ", code_str);
    uint16_t jump = GET_CODE_AT_CAST(uint16_t, chunk, offset) + sizeof(uint16_t);
    DEBUG_PRINT("%u", jump);
}

int debug_op_print(Chunk* chunk, int offset) {
    DEBUG_PRINT("%04d  ", offset);
    uint16_t line = GET_LINE_AT(chunk, offset);
    if(offset>0 && GET_LINE_AT(chunk, offset-1) == line) {
        DEBUG_PRINT("    |  ");
    } else {
        DEBUG_PRINT("%5d  ", line);
    }

    switch (GET_CODE_AT(chunk, offset))
    {
    case OP_RETURN:
        DEBUG_PRINT("OP_RETURN");
        return 1;
        break;
    case OP_JUMP:
        debug_jump_print("OP_JUMP", chunk, offset + 1);
        return 3;
        break;
    case OP_POP:
        DEBUG_PRINT("OP_POP");
        return 1;
        break;
    case OP_LCONST:
        debug_constant_print("OP_LCONST", chunk, offset + 1);
        return 2;
        break;
    case OP_DCONST:
        debug_constant_print("OP_DCONST", chunk, offset + 1);
        return 2;
        break;
    case OP_STRCONST:
        debug_constant_print("OP_STRCONST", chunk, offset + 1);
        return 2;
        break;
    case OP_BOOLTRUE:
        DEBUG_PRINT("OP_BOOLTRUE");
        return 1;
        break;
    case OP_BOOLFALSE:
        DEBUG_PRINT("OP_BOOLFALSE");
        return 1;
        break;
    case OP_JUMP_IF_FALSE:
        debug_jump_print("OP_JUMP_IF_FALSE", chunk, offset + 1);
        return 3;
        break;
    case OP_JUMP_IF_TRUE:
        debug_jump_print("OP_JUMP_IF_TRUE", chunk, offset + 1);
        return 3;
        break;
    case OP_DEFGLOBAL:
        debug_constant_print("OP_DEFGLOBAL", chunk, offset + 1);
        return 2;
        break;
    case OP_SETGLOBAL:
        debug_constant_print("OP_SETGLOBAL", chunk, offset + 1);
        return 2;
        break;
    case OP_GETGLOBAL:
        debug_constant_print("OP_GETGLOBAL", chunk, offset + 1);
        return 2;
        break;
    case OP_BLOCK:
        debug_local_print("OP_BLOCK", chunk, offset + 1);
        return 2;
    case OP_EXITBLOCK:
        DEBUG_PRINT("OP_EXITBLOCK");
        return 1;
    case OP_DEFLOCAL:
        debug_local_print("OP_DEFLOCAL", chunk, offset + 1);
        return 2;
    case OP_SETLOCAL:
        debug_local_print("OP_SETLOCAL", chunk, offset + 1);
        return 2;
    case OP_GETLOCAL:
        debug_local_print("OP_GETLOCAL", chunk, offset + 1);
        return 2;
    case OP_ADD:
        DEBUG_PRINT("OP_ADD");
        return 1;
        break;
    case OP_SUB:
        DEBUG_PRINT("OP_SUB");
        return 1;
    case OP_MUL:
        DEBUG_PRINT("OP_MUL");
        return 1;
    case OP_DIV:
        DEBUG_PRINT("OP_DIV");
        return 1;
        break;
    case OP_EXITVM:
        DEBUG_PRINT("OP_EXITVM");
        return 1;
        break;
    default:
        break;
    }
    PRINT_ERR_ARGS("ERROR %s:%d : op code not found %d\n\n",  __FILE__, __LINE__,
        GET_CODE_AT(chunk, offset));
    exit(1);
}

void debug_chunk_print(Chunk* chunk) {
    DEBUG_PRINT("/// Chunk ///\n");
    DEBUG_PRINT("/// constants ///\n");
    for (size_t i=0; i < chunk->constants.count; i++) {
        PRINT_VALUE(chunk->constants.values[i], stderr);
        DEBUG_PRINT("\n");
    }
    for (size_t offset = 0; offset < chunk->count;)
    {
        int incr = debug_op_print(chunk, offset);
        offset+=incr;
        DEBUG_PRINT("\n");
    }
 }

void debug_vm_dump(VM* vm) {
    DEBUG_PRINT("\n");
    DEBUG_PRINT("\n");
    DEBUG_PRINT(RED "##### DUMP ####\n" RESET);
    DEBUG_PRINT("///  VM   ///\n");
    DEBUG_PRINT("ip: %p\n", vm->ip);
    DEBUG_PRINT("/// stack ///\n");
    DEBUG_PRINT("count: %d\n", (int) (vm->stack_top - vm->stack));
    debug_stack_print(vm, "values:");
    debug_chunk_print(&vm->chunk);
    DEBUG_PRINT(RED "/////////////\n" RESET);
    DEBUG_PRINT("\n");
    DEBUG_PRINT("\n");
}

#endif
