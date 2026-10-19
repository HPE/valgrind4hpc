all: hello_mpi

ifdef LOCALHOST
MPI_INC = -I./localMPI
endif

hello_mpi:
	cc hello_mpi.c $(MPI_INC) -o hello_mpi
