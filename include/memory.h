#ifndef uza_memory_h
#define uza_memory_h

#include "common.h"

// prefer stack string buffer allocations
#define STRING_STACK_BUFF_LEN 256


#define ARRAY_GROWTH_FACTOR 2
#define MIN_ARRAY_CAP 8

#define ALLOCATE(type, count) \
    (type*)reallocate(NULL, 0, sizeof(type) * (count))

#define FREE_ARRAY(type, pointer, oldCount) \
    reallocate(pointer, sizeof(type) * (oldCount), 0)

#define GROW_CAPACITY(capacity) \
    (MAX(capacity * ARRAY_GROWTH_FACTOR, MIN_ARRAY_CAP))

#define GROW_ARRAY(type, ptr, old_count, new_count) \
    (type*) reallocate(ptr, sizeof(type) * (old_count), \
        sizeof(type) * (new_count))

void* reallocate(void* ptr, size_t old_size, size_t new_size);

#endif // uza_memory_h
