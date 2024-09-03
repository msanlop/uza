# Define variables
CC = gcc            # Compiler to use
CFLAGS = -Wall  # Compiler flags: -Wall enables all warnings, -g includes debugging info
TARGET = main   # The name of the output shared library
SRC = vm.c chunk.c memory.c debug.c value.c serializer.c main.c # Source file
OBJ = $(SRC:.c=.o)  # Object file derived from source file

DEBUG ?= 1

ifeq ($(DEBUG), 1)
    CFLAGS += -DDEBUG -g
else
    CFLAGS += -O2
endif


# Default target
all: $(TARGET)

# Link object files to create the shared library
$(TARGET): $(OBJ)
	$(CC) $(CFLAGS) -o $@ $^

# Compile source files into object files
%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

# Clean up build artifacts
clean:
	rm -f $(TARGET) $(OBJ)

# Phony targets
.PHONY: clean
