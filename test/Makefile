CC = clang
CFLAGS = -Wall -Wextra -I../src/vm -I/opt/homebrew/Cellar/cunit/2.1-3/include/
LDFLAGS = -lcunit -L/opt/homebrew/Cellar/cunit/2.1-3/lib

# SRC = ../src/vm/*
TARGET=test_vm
CFLAGS+=-I../src/vm/
TEST_SRC = test_vm.c
OBJ = $(SRC:.c=.o)  # Object file derived from source file
TEST_OBJS=$(TEST_SRC:.c=.o)

all: test

test: $(TARGET)
	./$(TARGET)

$(TARGET): $(TEST_OBJS)
	$(CC) $(CFLAGS) $^ $(LDFLAGS)  -o $@
	# ./test_vm

# Compile source files into object files
%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

# Clean up build artifacts
clean:
	rm -f $(TARGET) $(OBJ)

# Phony targets
.PHONY: all clean
