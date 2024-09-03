#if !defined(uza_object_h)
#define uza_object_h

#include "value.h"

typedef enum {
    OBJ_STRING,
} ObjectType;

struct Obj {
    ObjectType type;    
    struct Obj* next;
};

struct ObjectString{
    struct Obj obj;
    int length;
    char chars[];
} ;


#define OBJ_TYPE(object) (AS_OBJECT((object))->type)
#define IS_STRING(value) (IS_OBJECT(value) && (OBJ_TYPE(value) == OBJ_STRING))

#define AS_STRING(string_value) (((struct ObjectString* ) AS_OBJECT(string_value)))


struct ObjectString* object_string_allocate(int string_length);
void object_string_free(struct ObjectString* obj_string);


#endif // uza_object_h
