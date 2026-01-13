# Compilers
CC  = gcc
CXX = g++

# Utilities
ECHO = echo
RM   = rm -f

# Compiler flags
CFLAGS   = -Wall -Werror -ggdb -funroll-loops
CXXFLAGS = -Wall -Werror -ggdb -funroll-loops

# ncurses (wide) flags via pkg-config
CFLAGS   += $(shell pkg-config --cflags ncursesw)
CXXFLAGS += $(shell pkg-config --cflags ncursesw)
LDFLAGS  += $(shell pkg-config --libs ncursesw)

# Target
BIN = rogue

# Objects
OBJS = heap.o darray.o dice.o actor.o parsedesc.o dungeon.o rogue.o

# Default target
all: $(BIN)

# Link step (use gcc, link C++ explicitly)
$(BIN): $(OBJS)
	@$(ECHO) Linking $@
	@$(CC) $^ -lm -lstdc++ $(LDFLAGS) -o $@

# Dependency includes
-include $(OBJS:.o=.d)

# C compilation
%.o: %.c
	@$(ECHO) Compiling $<
	@$(CC) $(CFLAGS) -MMD -MF $*.d -c $<

# C++ compilation
%.o: %.cpp
	@$(ECHO) Compiling $<
	@$(CXX) $(CXXFLAGS) -MMD -MF $*.d -c $<

# Phony targets
.PHONY: all clean clobber

clean:
	@$(ECHO) Removing generated files
	@$(RM) *.o *.d $(BIN)

clobber: clean
	@$(ECHO) Removing backup files
	@$(RM) *~ \#*#
