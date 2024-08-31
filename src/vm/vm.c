#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#include "chunk.h"
#include "common.h"

typedef struct {
    uint8_t version[3];
    Chunk chunk;
} Program;

void print_program(Program *program) {
    printf("Program\n");
    printf("version: ");
    size_t i;
    for (i = 0; i < 2; i++)
    {
        printf("%d.", program->version[i]);
    }
    printf("%d", program->version[i]);
    printf("\n");
}

void read_program(char* filename) {
    Program program = {0};
    FILE *file = fopen(filename, "r");
    if (file == NULL) {
        fprintf(stderr, "FILE NOT FOUND");
        exit(1);
    }
    fread(program.version, sizeof(uint8_t), 3, file);
    fclose(file);
    print_program(&program);
}

int main(int arc, char** argv) {
    // char *filename = "../../target/test.zbc";
    // read_program(filename);
    Chunk chunk = {0};
    init_chunk(&chunk);
    int constant = add_constant(&chunk, 123.5);
    write_chunk(&chunk, OP_CONSTANT);
    write_chunk(&chunk, constant);
    write_chunk(&chunk, OP_RETURN);
    print_chunk(&chunk);
    free_chunk(&chunk);
    return 0;
}