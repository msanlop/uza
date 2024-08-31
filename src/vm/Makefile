# Define variables
CC = gcc            # Compiler to use
CFLAGS = -Wall -g   # Compiler flags: -Wall enables all warnings, -g includes debugging info
TARGET = vm # The name of the output executable
SRC = vm.c chunk.c memory.c value.c   # Source file
OBJ = $(SRC:.c=.o)  # Object file derived from source file

# Default target
all: $(TARGET)

# Link object files to create the executable
$(TARGET): $(OBJ)
	$(CC) $(CFLAGS) -o $@ $^

# Compile source files into object files
%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

# Clean up build artifacts
clean:
	rm -f $(TARGET) $(OBJ)

# Phony targets
.PHONY: all clean
