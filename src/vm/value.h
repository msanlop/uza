#if !defined(uza_value_h)
#define uza_value_h

#include "common.h"

typedef double Value;

typedef struct {
  int capacity;
  int count;
  Value* values;
} ValueArray;

void value_array_init(ValueArray* array);
void value_array_write(ValueArray* array, Value value);
void value_array_free(ValueArray* array);

#endif // uza_value_h