#if !defined(uza_value_h)
#define uza_value_h

#include "common.h"

typedef struct Obj Obj;
typedef struct ObjectString ObjectString;

typedef enum {
  TYPE_INVALID = -1,
  TYPE_NIL,
  TYPE_LONG,
  TYPE_BOOL,
  TYPE_DOUBLE,
  TYPE_OBJ,
} ValueType;

typedef struct {
  ValueType type;
  union {
    int64_t integer;
    double  fp;
    bool    boolean;
    struct Obj*    object;
  } as;
} Value;

#define VAL_NIL ((Value){TYPE_NIL, {.integer = 0}})
#define VAL_BOOL(val) ((Value) {TYPE_BOOL, .as.boolean=val})

#define IS_INTEGER(value) ((value).type == TYPE_LONG)
#define IS_DOUBLE(value) ((value).type == TYPE_DOUBLE)
#define IS_BOOL(value) ((value).type == TYPE_BOOL)
#define IS_OBJECT(value) ((value).type == TYPE_OBJ)
#define IS_NIL(value)     ((value).type == TYPE_NIL)

#define AS_INTEGER(value) ((value).as.integer)
#define AS_DOUBLE(value) ((value).as.fp)
#define AS_OBJECT(value) ((Obj*) (value).as.object)

#define I2D(value) \
  do { \
    (value).type = TYPE_DOUBLE; \
    (value).as.fp = (double) (value).as.integer; \
  } while (false); \


// TODO: change back to DEBUG_PRINT when able to
#define PRINT_VALUE(value, out) \
  do { \
    switch ((value).type) \
    { \
    case TYPE_NIL: \
      fprintf((out), "(nil)"); break; \
    case TYPE_LONG: \
      fprintf((out), "%lld", (value).as.integer); break; \
    case TYPE_DOUBLE: \
      fprintf((out), "%.3lf", (value).as.fp); break; \
    case TYPE_BOOL: \
      fprintf((out), "%d", (value).as.boolean); break; \
    case TYPE_OBJ: \
      if(AS_OBJECT(value)->type == OBJ_STRING) { \
        fprintf((out), "%s", ((ObjectString*) AS_OBJECT(value))->chars); \
      } \
      else { \
      } \
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
