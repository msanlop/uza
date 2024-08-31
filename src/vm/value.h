#if !defined(uza_value_h)
#define uza_value_h

#include "common.h"

typedef double Value;

typedef struct {
  int capacity;
  int count;
  Value* values;
} ValueArray;

void init_valueArray(ValueArray* array);
void write_valueArray(ValueArray* array, Value value);
void print_valueArray(ValueArray* array);
void free_valueArray(ValueArray* array);

#endif // uza_value_h