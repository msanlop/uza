#if !defined(uza_object_h)
#define uza_object_h

#include <string.h>
#include "table.h"
#include "chunk.h"
#include "native.h"

typedef enum {
    OBJ_STRING,
    OBJ_FUNCTION_NATIVE,
    OBJ_FUNCTION,
} ObjectType;

struct Obj {
    ObjectType type;
    bool is_marked;
    struct Obj* next;
};

typedef struct {
    struct Obj obj;
    int arity;
    union
    {
        Chunk *chunk;
        native_function function;
    };
    ObjectString *name;
} ObjectFunction;

struct ObjectString{
    struct Obj obj;
    int length;
    uint32_t hash;
    char chars[];
} ;


#define OBJ_TYPE(object) (AS_OBJECT((object))->type)
#define IS_STRING(value) (IS_OBJECT(value) && (OBJ_TYPE(value) == OBJ_STRING))


ObjectString* object_string_allocate(Table *strings, const char *chars, const int string_length);
void object_string_hash(struct ObjectString *string);
void object_string_free(struct ObjectString* obj_string);
struct ObjectString* object_string_concat(Table *strings, const struct ObjectString *lhs, const struct ObjectString *rhs);

ObjectFunction *object_function_allocate();

#endif // uza_object_h
