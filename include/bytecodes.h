#if !defined(uza_bytecodes_h)
#define uza_bytecodes_h

typedef enum {
    OP_RETURN,
    OP_LCONST,
    OP_DCONST,
    OP_STRCONST,
    OP_BOOLTRUE,
    OP_BOOLFALSE,
    OP_ADD,
    OP_SUB,
    OP_MUL,
    OP_DIV,
    OP_NEG,
    OP_DEFGLOBAL,
    OP_GETGLOBAL,
    OP_SETGLOBAL,
    OP_BLOCK,
    OP_EXITBLOCK,
    OP_DEFLOCAL,
    OP_GETLOCAL,
    OP_SETLOCAL,
    OP_EXITVM,
} OpCode;

#endif // uza_bytecodes_h
