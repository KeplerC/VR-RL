# Compiler
CC = gcc

# For example: -I$(INCDIR)
CFLAGS = -I$(INCDIR)

# Link libraries. For example: -lrt -lm
LIBS = -lrt

# For example: -std=c99 -std=c++11
FLAGS = -std=gnu99
# FLAGS =

INCDIR = include
OBJDIR = object
SRCDIR = source

_DEPS = moonskySocket.h
DEPS = $(patsubst %,$(INCDIR)/%,$(_DEPS))

_OBJ = main.o moonskySocket.o
OBJ = $(patsubst %,$(OBJDIR)/%,$(_OBJ))

$(OBJDIR)/%.o: $(SRCDIR)/%.c $(DEPS)
	$(CC) $(FLAGS) -c -o $@ $< $(CFLAGS)

Program: $(OBJ)
	$(CC) $(FLAGS) -o $@ $^ $(CFLAGS) $(LIBS)

.PHONY: clean

clean:
	rm -f $(OBJDIR)/*.o Program
