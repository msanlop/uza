#include "object.h"
#include "memory.h"
#include "value.h"
#include <assert.h>
#include <stdio.h>

// using the FNV-1a hashing algorithm
static uint32_t hash_string(const char *key, int length) {
  uint32_t hash = 2166136261u;
  for (int i = 0; i < length; i++) {
    hash ^= (uint8_t)key[i];
    hash *= 16777619;
  }
  return hash;
}

ObjectString *object_string_allocate(Table *strings, const char *chars,
                                     const int string_length) {
  uint32_t hash = hash_string(chars, string_length);
  ObjectString *res = tableFindString(strings, chars, string_length, hash);
  if (res != NULL) {
    return res;
  }

  size_t alloc_size =
      sizeof(Obj) + sizeof(int) + sizeof(uint32_t) + string_length + 1;

  vm.bytesAllocated += alloc_size;
#ifdef DEBUG_STRESS_GC
  collectGarbage();
#endif
  if (vm.bytesAllocated > vm.nextGC) {
    collectGarbage();
  }
  vm.nextGC = vm.bytesAllocated * GC_HEAP_GROW_FACTOR;

  ObjectString *str = calloc(1, alloc_size);
  str->length = string_length;
  memcpy(str->chars, chars, string_length);
  str->chars[string_length] = 0;
  str->obj.type = OBJ_STRING;
  str->obj.next = NULL;
  str->hash = hash;
  tableSet(strings, str, VAL_NIL);
  str->obj.next = vm.objects;
  vm.objects = (Obj *)str;
  return str;
}

void object_string_hash(struct ObjectString *string) {
  assert(string->hash == 0);
  string->hash = hash_string(string->chars, string->length);
}

ObjectString *object_string_concat(Table *strings, const ObjectString *lhs,
                                   const ObjectString *rhs) {
  char static_buff[STRING_STACK_BUFF_LEN];
  int new_len = lhs->length + rhs->length;
  char *buff = static_buff;
  if (new_len > STRING_STACK_BUFF_LEN) {
    buff = calloc(new_len + 1, sizeof(char));
    if (buff == NULL) {
      fprintf(stderr, "error: couldn't allocate to concat string\n");
      exit(1);
    }
  }
  buff[0] = 0;
  strncpy(buff, lhs->chars, lhs->length + 1);
  strncat(buff, rhs->chars, new_len);

  ObjectString *new_str = object_string_allocate(strings, buff, new_len);
  if (new_len > STRING_STACK_BUFF_LEN) {
    free(buff);
  }
  return new_str;
}

ObjectFunction *object_function_allocate() {
  size_t alloc_size = sizeof(ObjectFunction);
  vm.bytesAllocated += alloc_size;
#ifdef DEBUG_STRESS_GC
  collectGarbage();
#endif
  if (vm.bytesAllocated > vm.nextGC) {
    collectGarbage();
  }
  vm.nextGC = vm.bytesAllocated * GC_HEAP_GROW_FACTOR;

  ObjectFunction *function = (ObjectFunction *)calloc(1, alloc_size);
  function->obj.next = vm.objects;
  vm.objects = (Obj *)function;
  function->obj.type = OBJ_FUNCTION;
  function->arity = 0;
  function->name = NULL;
  // chunk_init(&function->chunk);
  return function;
}

void object_string_free(ObjectString *obj_string) { free(obj_string); }

ObjectList *object_list_allocate(void) {
  ObjectList *list = ALLOCATE(ObjectList, 1);
  value_array_init(&list->list);

  list->obj.type = OBJ_LIST;
  list->obj.next = vm.objects;
  vm.objects = &list->obj;

  return list;
}

void object_list_free(ObjectList *list) {
  value_array_free(&list->list);
  free(list);
}
