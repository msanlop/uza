#include <stdio.h>

#include "native.h"
#include "value.h"
#include "vm.h"

void native_println(void) {
  Value val = pop();
#ifndef NDEBUG
  fflush(stdout);
  DEBUG_PRINT(BRIGHT_RED "STDOUT PRINTLN:`" RESET);
  fflush(stderr);
#endif

  PRINT_VALUE(val, stdout);
  printf(NEWLINE);

#ifndef NDEBUG
  fflush(stdout);
  DEBUG_PRINT(BRIGHT_RED "`" RESET NEWLINE);
#endif
}

void native_print(void) {
  Value val = pop();
#ifndef NDEBUG
  fflush(stdout);
  DEBUG_PRINT(BRIGHT_RED "STDOUT PRINTLN:`" RESET);
  fflush(stderr);
#endif

  PRINT_VALUE(val, stdout);

#ifndef NDEBUG
  fflush(stdout);
  DEBUG_PRINT(BRIGHT_RED "`" RESET NEWLINE);
#endif
}

void native_list_construct(void) {
  ObjectList *list = object_list_allocate();
  push(VAL_OBJ(list));
}

void native_list_append(void) {
  Value val = pop();
  Value list = PEEK(vm);
  value_array_write(&AS_LIST(list)->list, val);
  pop();
}

void native_len(void) {
  Value val = pop();
  if (IS_LIST(val)) {
    push(VAL_INT(AS_LIST(val)->list.count));
  } else if (IS_STRING(val)) {
    push(VAL_INT(AS_STRING(val)->length));
  } else {
    PRINT_ERR("Called len on invalid value.");
    exit(1);
  }
}

void native_get(void) {
  Value index = pop();
  int i = index.as.integer;
  Value val = pop();
  if (IS_LIST(val)) {
    int list_count = AS_LIST(val)->list.count;
    if (i >= list_count) {
      PRINT_ERR_ARGS("Index out of bounds: %d for list of size %d.", i,
                     list_count);
      exit(1);
    }
    if (i < 0) {
      i = (i % list_count + list_count) % list_count;
    }
    push((AS_LIST(val)->list.values[i]));
  } else if (IS_STRING(val)) {
    int string_len = AS_STRING(val)->length;
    if (i >= string_len) {
      PRINT_ERR_ARGS("Index out of bounds: %d for string of length %d.", i,
                     string_len);
      exit(1);
    }
    if (i < 0) {
      i = (i % string_len + string_len) % string_len;
    }
    ObjectString *character =
        object_string_allocate(&vm.strings, &AS_STRING(val)->chars[i], 1);
    push(VAL_OBJ(character));
  } else {
    PRINT_ERR("Called get on invalid value.");
    exit(1);
  }
}

void native_set(void) {
  Value new_val = pop();
  Value index = pop();
  int i = index.as.integer;
  Value val = pop();
  if (IS_LIST(val)) {
    if (i >= AS_LIST(val)->list.count) {
      PRINT_ERR_ARGS("Index out of bounds: %d for list of size %d.", i,
                     AS_LIST(val)->list.count);
      exit(1);
    }

    AS_LIST(val)->list.values[i] = new_val;
  } else {
    PRINT_ERR("Called get on invalid value.");
    exit(1);
  }
}

void native_substring(void) {
  Value end_val = pop();
  Value start_val = pop();
  Value val = pop();
  int start = start_val.as.integer;
  int end = end_val.as.integer;
  if (IS_STRING(val)) {
    if (end > AS_STRING(val)->length) {
      PRINT_ERR_ARGS("Index out of bounds: %d for string of length %d.", end,
                     AS_STRING(val)->length);
      exit(1);
    }
    if (start < 0) {
      PRINT_ERR_ARGS("Index out of bounds: %d for string of length %d.", start,
                     AS_STRING(val)->length);
      exit(1);
    }
    ObjectString *character = object_string_allocate(
        &vm.strings, &AS_STRING(val)->chars[start], end - start);
    push(VAL_OBJ(character));
  } else {
    PRINT_ERR("Called do substring on invalid value.");
    exit(1);
  }
}

static int asc_cmp(const void *a, const void *b) {
  Value val_a = *(Value *)a;
  Value val_b = *(Value *)b;

  if (IS_INTEGER(val_a)) {
    return AS_INTEGER(val_a) - AS_INTEGER(val_b);
  } else if (IS_DOUBLE(val_a)) {
    return AS_DOUBLE(val_a) - AS_DOUBLE(val_b);
  } else {
    PRINT_ERR("Cannot sort type\n");
    exit(1);
  }
}

static int desc_cmp(const void *a, const void *b) {
  Value val_a = *(Value *)a;
  Value val_b = *(Value *)b;

  if (IS_INTEGER(val_a)) {
    return AS_INTEGER(val_b) - AS_INTEGER(val_a);
  } else if (IS_DOUBLE(val_a)) {
    return AS_DOUBLE(val_b) - AS_DOUBLE(val_a);
  } else {
    PRINT_ERR("Cannot sort type\n");
    exit(1);
  }
}

void native_sort(void) {
  Value desc = pop();
  Value list = pop();
  if (desc.as.boolean) {
    qsort(AS_LIST(list)->list.values, AS_LIST(list)->list.count, sizeof(Value),
          desc_cmp);
  } else {
    qsort(AS_LIST(list)->list.values, AS_LIST(list)->list.count, sizeof(Value),
          asc_cmp);
  }
}

const NativeFunction native_builtins[] = {
    {"print", sizeof("print") - 1, {(native_function)native_print}, 1},
    {"println", sizeof("println") - 1, {(native_function)native_println}, 1},
    {"List", sizeof("List") - 1, {(native_function)native_list_construct}, 0},
    {"append", sizeof("append") - 1, {(native_function)native_list_append}, 2},
    {"len", sizeof("len") - 1, {(native_function)native_len}, 1},
    {"get", sizeof("get") - 1, {(native_function)native_get}, 2},
    {"set", sizeof("set") - 1, {(native_function)native_set}, 3},
    {"substring",
     sizeof("substring") - 1,
     {(native_function)native_substring},
     3},
    {"sort", sizeof("sort") - 1, {(native_function)native_sort}, 1},
};

const NativeFunction *const native_functions_get(size_t *out_count) {
  *out_count = sizeof(native_builtins) / sizeof(NativeFunction);
  return native_builtins;
}
