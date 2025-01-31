#include "value.h"
#include "memory.h"

void value_array_init(ValueArray *array) {
  array->capacity = 0;
  array->count = 0;
  array->values = NULL;
}

void value_array_write(ValueArray *array, Value value) {
  size_t capacity_new = 0;
  if (array->count + 1 > array->capacity) {
    capacity_new = GROW_CAPACITY(array->capacity);
    Value *values_new =
        GROW_ARRAY(Value, array->values, array->capacity, capacity_new);
    array->values = values_new;
    array->capacity = capacity_new;
  }

  array->values[array->count] = value;
  array->count += 1;
}

void value_array_free(ValueArray *array) {
  FREE_ARRAY(Value, array->values, array->capacity);
  value_array_init(array);
}

void value_array_print(ValueArray *array, FILE *out) {
  fprintf(out, "[");
  int i;
  for (i = 0; i < array->count - 1; i++) {
    PRINT_VALUE(array->values[i], out);
    fprintf(out, ", ");
  }

  if (i < array->count) {
    PRINT_VALUE(array->values[i], out);
  }
  fprintf(out, "]");
}
