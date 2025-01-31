#if !defined(uza_object_h)
#define uza_object_h

#include "chunk.h"
#include "native.h"
#include "table.h"
#include "value.h"
#include <string.h>

typedef enum {
  OBJ_STRING,
  OBJ_FUNCTION_NATIVE,
  OBJ_FUNCTION,
  OBJ_LIST,
} ObjectType;

struct Obj {
  ObjectType type;
  bool is_marked;
  struct Obj *next;
};

typedef struct {
  struct Obj obj;
  int arity;
  union {
    Chunk *chunk;
    native_function function;
  };
  ObjectString *name;
} ObjectFunction;

struct ObjectString {
  struct Obj obj;
  int length;
  uint32_t hash;
  char chars[];
};

typedef struct {
  struct Obj obj;
  ValueArray list;
} ObjectList;

#define OBJ_TYPE(object) (AS_OBJECT((object))->type)
#define IS_STRING(value) (IS_OBJECT(value) && (OBJ_TYPE(value) == OBJ_STRING))
#define IS_LIST(value) (IS_OBJECT(value) && (OBJ_TYPE(value) == OBJ_LIST))

ObjectString *object_string_allocate(Table *strings, const char *chars,
                                     const int string_length);
void object_string_hash(struct ObjectString *string);
void object_string_free(struct ObjectString *obj_string);
struct ObjectString *object_string_concat(Table *strings,
                                          const struct ObjectString *lhs,
                                          const struct ObjectString *rhs);

ObjectFunction *object_function_allocate(void);

ObjectList *object_list_allocate(void);
void object_list_free(ObjectList *list);

#endif // uza_object_h
