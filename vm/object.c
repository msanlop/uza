#include "object.h"
#include "value.h"
#include "memory.h"
#include <assert.h>

// using the FNV-1a hashing algorithm
static uint32_t hash_string(const char* key, int length) {
    uint32_t hash = 2166136261u;
    for (int i = 0; i < length; i++) {
    hash ^= (uint8_t)key[i];
    hash *= 16777619;
    }
    return hash;
}

ObjectString* object_string_allocate(const int string_length) {
    ObjectString* str = calloc(
        1,
        sizeof(Obj) + sizeof(int) + sizeof(uint32_t) + string_length + 1
    );
    str->length = string_length;
    str->obj.type = OBJ_STRING;
    str->hash = 0;
    return str;
}

void object_string_hash(struct ObjectString *string) {
    assert(string->hash == 0);
    string->hash = hash_string(string->chars, string->length);
}

ObjectString* object_string_concat(const ObjectString *lhs, const ObjectString *rhs) {
    int new_len = lhs->length + rhs->length;
    ObjectString* new_object_string = object_string_allocate(new_len);
    strncpy(new_object_string->chars, lhs->chars, lhs->length + 1);
    strncat(
        new_object_string->chars,
        rhs->chars,
        new_len
    );
    new_object_string->hash = hash_string(new_object_string->chars, new_len);
    return new_object_string;
}

void object_string_free(ObjectString* obj_string) {
    free(obj_string);
}
