#ifndef uza_native_h
#define uza_native_h

#include "common.h"

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#else
#include <time.h>
#ifdef __MACH__
#include <mach/kern_return.h>
#include <mach/mach_time.h>
#endif
#endif

#define TABLE_ENTRY(key_string, native_function)

typedef void (*native_function)(void);

typedef struct {
  const char *const name;
  const size_t name_len;
  const native_function function;
  const size_t arity; // unused so far
} NativeFunction;

#define NEW_NATIVE_FUNCTION(name, func_name, arity)                            \
  {name, sizeof(name) - 1, (native_function)func_name, arity}

const NativeFunction *const native_functions_get(size_t *out_count);

#endif
