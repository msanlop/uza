#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "chunk.h"
#include "common.h"
#include "serializer.h"

typedef struct {
    uint8_t version[3];
    Chunk chunk;
} Program;

void print_program(Program* program) {
    printf("Program\n");
    printf("version: ");
    size_t i;
    for (i = 0; i < 2; i++) {
        printf("%d.", program->version[i]);
    }
    printf("%d", program->version[i]);
    printf("\n");
}

void read_program(char* filename) {
    Program program = {0};
    FILE* file = fopen(filename, "r");
    if (file == NULL) {
        fprintf(stderr, "FILE NOT FOUND");
        exit(1);
    }
    fread(program.version, sizeof(uint8_t), 3, file);
    fclose(file);
    print_program(&program);
}

// int main(int arc, char** argv) {
//     // char *filename = "../../target/test.zbc";
//     // read_program(filename);
//     printf("%lu\n", sizeof(Value));
//     Chunk chunk = {0};
//     init_chunk(&chunk);
//     int constant = add_constant(&chunk, 123.5);
//     write_chunk(&chunk, OP_CONSTANT);
//     write_chunk(&chunk, constant);
//     write_chunk(&chunk, OP_RETURN);
//     print_chunk(&chunk);
//     free_chunk(&chunk);
//     return 0;
// }

int main(int arc, char** argv) {
    char* filename = "../../target/test.uza";
    FILE* file = fopen(filename, "r");
    if (file == NULL) {
        PRINT_ERR("Could not open ");
        fprintf(stderr, "'%s'\n", filename);
    }
    for (size_t i = 0; i < 3; i++) {
        uint8_t num = 0;
        fread(&num, 1, 1, file);
        printf("%hhu", num);
    }
    printf("\n");
    Chunk chunk = {0};
    init_chunk(&chunk);
    load_chunk(file, &chunk);
    print_chunk(&chunk);
    return 0;
}