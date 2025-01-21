#include <stdio.h>

#include "memory.h"
#include "common.h"
#include "vm.h"


#ifdef DEBUG_LOG_GC
#include "debug.h"
#endif

extern bool enable_garbage_collection;

void* reallocate(void* ptr, size_t old_size, size_t new_size) {
    if (new_size > old_size) {
#ifdef DEBUG_STRESS_GC
        collectGarbage();
#endif
    }

    if(new_size == 0 ) {
        free(ptr);
        return NULL;
    }

    void* new_ptr = realloc(ptr, new_size);
    if (new_ptr == NULL) {
        PRINT_ERR("Could not reallocate. Exiting...");
        exit(1);
    }
    return new_ptr;
}

void object_free(Obj *obj) {
    switch (obj->type)
    {
    case OBJ_STRING:
        object_string_free(obj);
        break;
    default:
        break;
    }
}

void markValue(Value value) {
  if (IS_OBJECT(value)) markObject(AS_OBJECT(value));
}

void markObject(Obj* object) {
  if (object == NULL) return;
  if (object->is_marked) return;
  object->is_marked = true;

  if (vm.gray_capacity < vm.gray_count + 1) {
    vm.gray_capacity = GROW_CAPACITY(vm.gray_capacity);
    vm.gray_stack = (Obj**)realloc(vm.gray_stack,
                                  sizeof(Obj*) * vm.gray_capacity);
  }

  vm.gray_stack[vm.gray_count++] = object;
  if (vm.gray_stack == NULL) exit(1);

}

static void markArray(ValueArray* array) {
  for (int i = 0; i < array->count; i++) {
    markValue(array->values[i]);
  }
}

static void blackenObject(Obj* object) {
#ifdef DEBUG_LOG_GC
  DEBUG_PRINT("%p blacken ", (void*)object);
  PRINT_VALUE(VAL_OBJ(object), stderr);
  DEBUG_PRINT(NEWLINE);
#endif
  switch (object->type) {
    case OBJ_FUNCTION_NATIVE: {
        ObjectFunction * func = (ObjectFunction *) object;
        markObject(func->name);
        break;
    }
    case OBJ_FUNCTION: {
        ObjectFunction * func = (ObjectFunction *) object;
        markObject(func->name);
        markArray(&func->chunk->constants);
        break;
    }
    case OBJ_STRING:
      break;
  }
}

static void traceReferences() {
  while (vm.gray_count > 0) {
    Obj* object = vm.gray_stack[--vm.gray_count];
    blackenObject(object);
  }
}

static void markRoots() {
  for (Value* slot = vm.stack; slot < vm.stack_top; slot++) {
    markValue(*slot);
  }

  for (int i = 0; i <= vm.depth; i++) {
    markObject((Obj*)vm.frame_stacks[i].function);
  }
    markTable(&vm.globals);
}


void sweep() {
  Obj* previous = NULL;
  Obj* object = vm.objects;
  while (object != NULL) {
    if (object->is_marked) {
        object->is_marked = false;
      previous = object;
      object = object->next;
    } else {
    DEBUG_PRINT("freeing object: ");
    PRINT_VALUE(VAL_OBJ(object), stderr);
    DEBUG_PRINT(NEWLINE);
      Obj* unreached = object;
      object = object->next;
      if (previous != NULL) {
        previous->next = object;
      } else {
        vm.objects = object;
      }

      free(unreached);
    }
  }
}

void collectGarbage(){
    if (!enable_garbage_collection) return;
#ifdef DEBUG_LOG_GC
    DEBUG_PRINT(BRIGHT_YELLOW "-- GC BEGIN --\n" RESET);
#endif
    markRoots();
    traceReferences();
    tableRemoveWhite(&vm.strings);
    sweep();

#ifdef DEBUG_LOG_GC
    DEBUG_PRINT(BRIGHT_YELLOW "-- GC END --\n" RESET);
#endif

}
