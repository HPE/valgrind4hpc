MPI_SRC := $(wildcard mpi_*.c)
SHMEM_SRC := $(wildcard shmem_*.c)

SHMEM_PRESENT := $(shell cc shmem_no_error.c >/dev/null 2>&1 && echo yes; rm -f a.out)

SRC = $(MPI_SRC)
ifeq ($(SHMEM_PRESENT),yes)
	SRC += $(SHMEM_SRC)
endif

BIN = $(SRC:.c=)

# ANSI escape codes
IN_YELLOW = \033[93m
NO_COLOR = \033[0m

all: $(BIN)
ifneq ($(SHMEM_PRESENT),yes)
	@echo -e "$(IN_YELLOW)cray-shmem not found, skipping tests that require it."
	@echo -e "$(IN_YELLOW)To build these tests, load cray-shmem so that the cc compiler can find it."
	@echo -ne "$(NO_COLOR)"
endif

% : %.c
	cc -g -O0 $(CFLAGS) $< -o $@ $(LDFLAGS)

clean:
	rm -f $(BIN)
