#if !defined(uza_value_h)
#define uza_value_h

#include "common.h"


typedef enum {
  TYPE_INVALID = -1,
  TYPE_LONG,
  TYPE_BOOL,
  TYPE_DOUBLE,
} ValueType;

typedef struct {
  ValueType type;
  union {
    int64_t integer;
    double  fp;
    bool    boolean;
  } as;
} Value;

#define IS_INTEGER(value) ((value).type == TYPE_LONG)
#define IS_DOUBLE(value) ((value).type == TYPE_DOUBLE)
#define IS_BOOL(value) ((value).type == TYPE_BOOL)

#define AS_INTEGER(value) ((value).as.integer)
#define AS_DOUBLE(value) ((value).as.fp)

#define I2D(value) \
  do { \
    (value).type = TYPE_DOUBLE; \
    (value).as.fp = (double) (value).as.integer; \
  } while (false); \
  


#define PRINT_VALUE(value) \
  do { \
    switch ((value).type) \
    { \
    case TYPE_LONG: \
      fprintf(stderr, "%lld", (value).as.integer); break; \
    case TYPE_DOUBLE: \
      fprintf(stderr, "%.3lf", (value).as.fp); break; \
    case TYPE_BOOL: \
      fprintf(stderr, "%d", (value).as.boolean); break; \
    default: break; \
    } \
  } while (false); \
  

typedef struct {
  int capacity;
  int count;
  Value* values;
} ValueArray;

void value_array_init(ValueArray* array);
void value_array_write(ValueArray* array, Value value);
void value_array_free(ValueArray* array);

#endif // uza_value_h