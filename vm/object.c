#include "object.h"
#include "value.h"
#include "memory.h"
#include <assert.h>
#include <stdio.h>

// using the FNV-1a hashing algorithm
static uint32_t hash_string(const char* key, int length) {
    uint32_t hash = 2166136261u;
    for (int i = 0; i < length; i++) {
    hash ^= (uint8_t)key[i];
    hash *= 16777619;
    }
    return hash;
}

ObjectString* object_string_allocate(Table *strings, const char *chars, const int string_length) {
    uint32_t hash = hash_string(chars, string_length);
    ObjectString *res = tableFindString(strings, chars, string_length, hash);
    if (res != NULL) {
        return res;
    }

    ObjectString* str = calloc(
        1,
        sizeof(Obj) + sizeof(int) + sizeof(uint32_t) + string_length + 1
    );
    str->length = string_length;
    memcpy(str->chars, chars, string_length);
    str->chars[string_length] = 0;
    str->obj.type = OBJ_STRING;
    str->hash = hash;
    tableSet(strings, str, VAL_NIL);
    return str;
}

void object_string_hash(struct ObjectString *string) {
    assert(string->hash == 0);
    string->hash = hash_string(string->chars, string->length);
}

ObjectString* object_string_concat(Table *strings, const ObjectString *lhs, const ObjectString *rhs) {
    char static_buff[STRING_STACK_BUFF_LEN];
    int new_len = lhs->length + rhs->length;
    char *buff = static_buff;
    if (new_len > STRING_STACK_BUFF_LEN) {
        buff = calloc(new_len + 1, sizeof(char));
        if(buff == NULL) {
            fprintf(stderr, "error: couldn't allocate to concat string\n");
            exit(1);
        }

    }
    buff[0] = 0;
    strncpy(buff, lhs->chars, lhs->length + 1);
    strncat(
        buff,
        rhs->chars,
        new_len
    );
    uint32_t hash = hash_string(buff, new_len);

    ObjectString *new_str = object_string_allocate(strings, buff, new_len);
    if (new_len > STRING_STACK_BUFF_LEN) {
        free(buff);
    }
    return new_str;
}

ObjectFunction *object_function_allocate() {
    ObjectFunction* function = (ObjectFunction *) calloc(1, sizeof(ObjectFunction));
    function->obj.type = OBJ_FUNCTION;
    function->arity = 0;
    function->name = NULL;
    chunk_init(&function->chunk);
    return function;
}

void object_string_free(ObjectString* obj_string) {
    free(obj_string);
}
