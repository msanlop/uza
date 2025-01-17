#if !defined(uza_object_h)
#define uza_object_h

#include <string.h>
#include "table.h"
#include "chunk.h"
#include "native.h"
#include "value.h"

typedef enum {
    OBJ_STRING,
    OBJ_FUNCTION_NATIVE,
    OBJ_FUNCTION,
} ObjectType;

struct Obj {
    ObjectType type;
    uint32_t ref_count;
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
};

#define ARC_INCREMENT(object_value) \
    do {                                                                       \
        AS_OBJECT(object_value)->ref_count++;                                        \
    } while (0);                                                               \

#ifndef NDEBUG
#define ARC_DECREMENT(value) \
    printf("ARC decr @:" " %s:%d" "\n", __FILE__, __LINE__);                   \
    do {                                                                       \
        if (IS_OBJECT(value)) {                                        \
            (AS_OBJECT((value))->ref_count) -= 1;                              \
            uint32_t refs = (AS_OBJECT((value))->ref_count);                   \
            if (refs == 0) {                                                   \
                object_free(&(value));                                         \
                printf("\tARC free:" " %s:%d" "\n", __FILE__, __LINE__);       \
            }                                                                  \
        }                                                                      \
    } while (0);    
#else
#define ARC_DECREMENT(value) \
    do {                                                                       \
        if ((value).type == TYPE_OBJ) {                                        \
            (AS_OBJECT((value))->ref_count) -= 1;                              \
            uint32_t refs = (AS_OBJECT((value))->ref_count);                   \
            if (refs == 0) object_free(&(value));                              \
        }                                                                      \
    } while (0);    
#endif

#define OBJ_TYPE(object) (AS_OBJECT((object))->type)
#define IS_STRING(value) (IS_OBJECT(value) && (OBJ_TYPE(value) == OBJ_STRING))


ObjectString* object_string_allocate(Table *strings, const char *chars, const int string_length);
void object_string_hash(struct ObjectString *string);
void object_string_free(struct ObjectString* obj_string);
struct ObjectString* object_string_concat(Table *strings, const struct ObjectString *lhs, const struct ObjectString *rhs);

ObjectFunction *object_function_allocate();
ObjectFunction *object_function_free(ObjectFunction *func);

void object_free(Value *val);

#endif // uza_object_h
