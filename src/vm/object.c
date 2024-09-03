#include "object.h"
#include "value.h"
#include "memory.h"

ObjectString* object_string_allocate(int string_length) {
    ObjectString* str = calloc(
        1,
        sizeof(Obj) + sizeof(int) + string_length + 1
    );
    return str;
}

void object_string_free(ObjectString* obj_string) {
    free(obj_string);
}