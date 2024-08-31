#include "value.h"
#include "memory.h"

void init_valueArray(ValueArray* array) {
    array->capacity = 0;
    array->count = 0;
    array->values = NULL;
}

void write_valueArray(ValueArray* array, Value value) {
    size_t capacity_new = 0;
    if(array->count + 1 > array->capacity) {
        capacity_new = GROW_CAPACITY(array->capacity);
        Value* values_new = GROW_ARRAY(Value, array->values, array->capacity, capacity_new);
        array->values = values_new;
        array->capacity = capacity_new;
    }

    array->values[array->count] = value;
    array->count += 1;
}

void free_valueArray(ValueArray* array) {
    FREE_ARRAY(Value, array->values, array->capacity);
    init_valueArray(array);
}