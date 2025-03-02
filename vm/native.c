#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "native.h"
#include "value.h"
#include "vm.h"

#ifdef _WIN32
#include <windows.h>
static LARGE_INTEGER frequency = {.QuadPart = -1LL};
#endif

static bool rand_seed_set = false;

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
  push(VAL_NIL);
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
  push(VAL_NIL);
}

void native_flush(void) {
  fflush(stdout);
  push(VAL_NIL);
}

void native_list_construct(void) {
  ObjectList *list = object_list_allocate();
  push(VAL_OBJ(list));
}

void native_list_append(void) {
  Value val = PEEK_AT(0);
  Value list = PEEK_AT(1);
  value_array_write(&AS_LIST(list)->list, val);
  POP_COUNT(2);
  push(VAL_NIL);
}

void native_len(void) {
  Value res = VAL_NIL;

  Value val = PEEK(vm);
  if (IS_LIST(val)) {
    res = (VAL_INT(AS_LIST(val)->list.count));
  } else if (IS_STRING(val)) {
    res = (VAL_INT(AS_STRING(val)->length));
  } else {
    PRINT_ERR("Called len on invalid value.");
    exit(1);
  }
  POP_COUNT(1);
  push(res);
}

void native_get(void) {
  Value res = VAL_NIL;

  Value index = PEEK_AT(0);
  int i = index.as.integer;
  Value val = PEEK_AT(1);
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
    res = ((AS_LIST(val)->list.values[i]));
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
    res = (VAL_OBJ(character));
  } else {
    PRINT_ERR("Called get on invalid value.");
    exit(1);
  }
  POP_COUNT(2);
  push(res);
}

void native_set(void) {
  Value new_val = PEEK_AT(0);
  Value index = PEEK_AT(1);
  int i = index.as.integer;
  Value val = PEEK_AT(2);
  if (IS_LIST(val)) {
    if (i >= AS_LIST(val)->list.count) {
      PRINT_ERR_ARGS("Index out of bounds: %d for list of size %d.", i,
                     AS_LIST(val)->list.count);
      exit(1);
    }

    AS_LIST(val)->list.values[i] = new_val;
  } else {
    PRINT_ERR("Called set on invalid value.");
    exit(1);
  }
  POP_COUNT(3);
  push(VAL_NIL);
}

void native_substring(void) {
  Value res = VAL_NIL;

  Value end_val = PEEK_AT(0);
  Value start_val = PEEK_AT(1);
  Value val = PEEK_AT(2);
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
    res = (VAL_OBJ(character));
  } else {
    PRINT_ERR("Called do substring on invalid value.");
    exit(1);
  }
  POP_COUNT(3);
  push(res);
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
  push(VAL_NIL);
}

void native_time_ns() {
  Value ret;
#ifdef _WIN32
  LARGE_INTEGER ticks;
  if (frequency.QuadPart == -1)
    QueryPerformanceFrequency(&frequency);

  QueryPerformanceCounter(&ticks);
  ret = VAL_INT(
      (uint64_t)((ticks.QuadPart * 1000000000ULL) / frequency.QuadPart));
#elif defined(__MACH__)
  ret = VAL_INT((uint64_t)clock_gettime_nsec_np(CLOCK_MONOTONIC_RAW));
#else
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
  ret = VAL_INT((uint64_t)(ts.tv_sec * 1000000000ULL + ts.tv_nsec));
#endif
  push(ret);
}

void native_time_ms() {
  Value ret;
#ifdef _WIN32
  LARGE_INTEGER ticks;
  if (frequency.QuadPart == -1)
    QueryPerformanceFrequency(&frequency);

  QueryPerformanceCounter(&ticks);
  ret = VAL_INT((uint64_t)((ticks.QuadPart * 1000ULL) / frequency.QuadPart));
#else
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
  ret = VAL_INT((uint64_t)(ts.tv_sec * 1000ULL + ts.tv_nsec / 1000000ULL));
#endif
  push(ret);
}

void native_abs() {
  Value a = pop();
  if (IS_INTEGER(a)) {
    push(VAL_INT(llabs(a.as.integer)));
  } else {
    push(VAL_FLOAT(fabs(a.as.fp)));
  }
}

void native_rand_int() {
  Value a = pop();
  if (!rand_seed_set) {
    srand(time(NULL));
    rand_seed_set = true;
  }
  int val = rand();
  val = (val * AS_INTEGER(a)) / RAND_MAX;
  push(VAL_INT(val));
}

void native_sleep(void) {
  Value a = pop();
  int milliseconds = a.as.integer;
#ifdef WIN32
  Sleep(milliseconds);
#else
  struct timespec ts;
  ts.tv_sec = milliseconds / 1000;
  ts.tv_nsec = (milliseconds % 1000) * 1000000;
  nanosleep(&ts, NULL);
#endif
  push(VAL_NIL);
}

const NativeFunction native_builtins[] = {
    NEW_NATIVE_FUNCTION("print", native_print, 1),
    NEW_NATIVE_FUNCTION("println", native_println, 1),
    NEW_NATIVE_FUNCTION("flush", native_flush, 0),
    NEW_NATIVE_FUNCTION("List", native_list_construct, 0),
    NEW_NATIVE_FUNCTION("append", native_list_append, 2),
    NEW_NATIVE_FUNCTION("len", native_len, 1),
    NEW_NATIVE_FUNCTION("get", native_get, 2),
    NEW_NATIVE_FUNCTION("set", native_set, 3),
    NEW_NATIVE_FUNCTION("substring", native_substring, 3),
    NEW_NATIVE_FUNCTION("sort", native_sort, 1),
    NEW_NATIVE_FUNCTION("timeNs", native_time_ns, 0),
    NEW_NATIVE_FUNCTION("timeMs", native_time_ms, 0),
    NEW_NATIVE_FUNCTION("abs", native_abs, 1),
    NEW_NATIVE_FUNCTION("randInt", native_rand_int, 1),
    NEW_NATIVE_FUNCTION("sleep", native_sleep, 1),
};

const NativeFunction *const native_functions_get(size_t *out_count) {
  *out_count = sizeof(native_builtins) / sizeof(NativeFunction);
  return native_builtins;
}
