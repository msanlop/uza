// https://github.com/munificent/craftinginterpreters/blob/master/c/table.h

// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to
// deal in the Software without restriction, including without limitation the
// rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
// sell copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:

// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.

// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
// FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
// IN THE SOFTWARE.

//> Hash Tables table-h
#ifndef uza_table_h
#define uza_table_h

#include "common.h"
#include "value.h"
//> entry

typedef struct ObjectString ObjectString;

typedef struct {
  ObjectString *key;
  Value value;
} Entry;
//< entry

typedef struct {
  int count;
  int capacity;
  Entry *entries;
} Table;

//> init-table-h
void initTable(Table *table);
//> free-table-h
void freeTable(Table *table);
//< free-table-h
//> table-get-h
bool tableGet(Table *table, ObjectString *key, Value *value);
//< table-get-h
//> table-set-h
bool tableSet(Table *table, ObjectString *key, Value value);
//< table-set-h
//> table-delete-h
bool tableDelete(Table *table, ObjectString *key);
//< table-delete-h
//> table-add-all-h
void tableAddAll(Table *from, Table *to);
//< table-add-all-h
//> table-find-string-h
ObjectString *tableFindString(Table *table, const char *chars, int length,
                              uint32_t hash);
//< table-find-string-h
//> Garbage Collection table-remove-white-h

void tableRemoveWhite(Table *table);
//< Garbage Collection table-remove-white-h
//> Garbage Collection mark-table-h
void markTable(Table *table);
//< Garbage Collection mark-table-h

//< init-table-h
#endif
