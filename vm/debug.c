#include "debug.h"
#include "common.h"

#ifndef NDEBUG

void debug_stack_print(char* str) {
    DEBUG_PRINT("%s\n" CYAN , str);
    Frame *frame = &vm.frame_stacks[vm.depth];
    for (Value* slot = &frame->locals[frame->locals_count]; slot < vm.stack_top; slot++) {
        PRINT_VALUE((*slot), stderr);
        DEBUG_PRINT("\n")
    }
    DEBUG_PRINT(RESET "----------\n");
}

void debug_locals_print(char* str) {
    DEBUG_PRINT("%s :\n" GREEN , str);
    if (vm.depth > 0) {
        Frame *frame = &vm.frame_stacks[vm.depth];
        for (int i = 0; i < frame->locals_count; i++) {
            DEBUG_PRINT("local #%d: ", i);
            PRINT_VALUE((frame->locals[i]), stderr);
            DEBUG_PRINT("\n")
        }
    }
    DEBUG_PRINT(RESET "----------\n");
}

void debug_local_print(char* code_str, Chunk* chunk, int offset){
    DEBUG_PRINT_TO("%-20s", code_str);
    int local = GET_CODE_AT(chunk, offset);
    DEBUG_PRINT("#%-5d", local);
}

void debug_constant_print(char* code_str, Chunk* chunk, int offset){
    DEBUG_PRINT_TO("%-20s", code_str);
    int constant = GET_CODE_AT(chunk, offset);
    DEBUG_PRINT("#%-5d" GREEN "// ", constant);
    PRINT_VALUE(chunk->constants.values[constant],stderr);
    DEBUG_PRINT(RESET);
}

void debug_jump_print(char* code_str, Chunk* chunk, int offset){
    DEBUG_PRINT_TO("%-20s", code_str);
    uint16_t jump = GET_CODE_AT_CAST(uint16_t, chunk, offset) + sizeof(uint16_t);
    DEBUG_PRINT("%u", jump);
}

int debug_op_print(Chunk* chunk, int offset) {
    switch (GET_CODE_AT(chunk, offset))
    {
    case OP_RETURN:
        DEBUG_PRINT_TO("%-20s", "OP_RETURN");
        return 1;
        break;
    case OP_CALL:
        DEBUG_PRINT_TO("%-20s", "OP_CALL");
        return 1;
        break;
    case OP_CALL_NATIVE:
        debug_constant_print("OP_CALL_NATIVE", chunk, offset + 1);
        return 2;
        break;
    case OP_JUMP:
        debug_jump_print("OP_JUMP", chunk, offset + 1);
        return 3;
        break;
    case OP_LOOP:
        debug_jump_print("OP_LOOP", chunk, offset + 1);
        return 3;
        break;
    case OP_POP:
        DEBUG_PRINT_TO("%-20s", "OP_POP");
        return 1;
        break;
    case OP_LFUNC:
        DEBUG_PRINT_TO("%-20s", "OP_LFUNC")
        return 2;
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
        DEBUG_PRINT_TO("%-20s", "OP_BOOLTRUE");
        return 1;
        break;
    case OP_TOSTRING:
        DEBUG_PRINT_TO("%-20s", "OP_TOSTRING");
        return 1;
        break;
    case OP_TOINT:
        DEBUG_PRINT_TO("%-20s", "OP_TOINT");
        return 1;
        break;
    case OP_TOFLOAT:
        DEBUG_PRINT_TO("%-20s", "OP_TOFLOAT");
        return 1;
        break;
    case OP_BOOLFALSE:
        DEBUG_PRINT_TO("%-20s", "OP_BOOLFALSE");
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
        DEBUG_PRINT_TO("%-20s", "OP_ADD");
        return 1;
        break;
    case OP_EQ:
        DEBUG_PRINT_TO("%-20s", "OP_EQ");
        return 1;
        break;
    case OP_NE:
        DEBUG_PRINT_TO("%-20s", "OP_NE");
        return 1;
        break;
    case OP_LT:
        DEBUG_PRINT_TO("%-20s", "OP_LT ( < )");
        return 1;
        break;
    case OP_LE:
        DEBUG_PRINT_TO("%-20s", "OP_LE ( <= )");
        return 1;
        break;
    case OP_GT:
        DEBUG_PRINT_TO("%-20s", "OP_GT ( > )");
        return 1;
        break;
    case OP_GE:
        DEBUG_PRINT_TO("%-20s", "OP_GE ( >= )");
        return 1;
        break;
    case OP_NOT:
        DEBUG_PRINT_TO("%-20s", "OP_NOT ( not )");
        return 1;
        break;
    case OP_SUB:
        DEBUG_PRINT_TO("%-20s", "OP_SUB");
        return 1;
    case OP_MUL:
        DEBUG_PRINT_TO("%-20s", "OP_MUL");
        return 1;
    case OP_DIV:
        DEBUG_PRINT_TO("%-20s", "OP_DIV");
        return 1;
        break;
    case OP_MOD:
        DEBUG_PRINT_TO("%-20s", "OP_MOD");
        return 1;
        break;
    case OP_NEG:
        DEBUG_PRINT_TO("%-20s", "OP_NEG");
        return 1;
        break;
    case OP_EXITVM:
        DEBUG_PRINT_TO("%-20s", "OP_EXITVM");
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
    DEBUG_PRINT("/// constants ///\n");
    for (size_t i=0; i < chunk->constants.count; i++) {
        PRINT_VALUE(chunk->constants.values[i], stderr);
        DEBUG_PRINT("\n");
    }
    DEBUG_PRINT("there are %ld ops\n", chunk->count);
    size_t offset = 0;
    for (size_t i = 0; i < chunk->count; i++)
    {
        DEBUG_PRINT("%04ld  ", i);

        uint16_t line = GET_LINE_AT(chunk, i);
        if(i>0 && GET_LINE_AT(chunk, i-1) == line) {
            DEBUG_PRINT("    |  ");
        } else {
            DEBUG_PRINT("%5d  ", line);
        }

        int incr = debug_op_print(chunk, offset);
        offset+=incr;
        DEBUG_PRINT("\n");
    }
 }

void debug_vm_dump(void) {
    DEBUG_PRINT("\n");
    DEBUG_PRINT("\n");
    DEBUG_PRINT(BLUE "##### DUMP ####\n" RESET);
    DEBUG_PRINT("///  VM   ///\n");
    DEBUG_PRINT("ip: %p\n", vm.frame_stacks[vm.depth].ip);
    DEBUG_PRINT("/// stack ///\n");
    DEBUG_PRINT("count: %d\n", (int) (vm.stack_top - vm.stack));
    debug_stack_print("values:");
    for (size_t i = 0; i < vm.chunk_count; i++)
    {
        DEBUG_PRINT("/// Chunk %ld ///\n", i);
        debug_chunk_print(vm.chunks[i]);
        DEBUG_PRINT(NEWLINE);
    }
    DEBUG_PRINT(BLUE "/////////////\n" RESET);
    DEBUG_PRINT("\n");
    DEBUG_PRINT("\n");
}

#endif
