/*
 Copyright 2019-2020 Hewlett Packard Enterprise Development LP
 Unpublished Proprietary Information.
 This unpublished work is protected to trade secret, copyright and other laws.
 Except as permitted by contract or express written permission of Hewlett
 Packard Enterprise Development LP., no part of this work or its content may be
 used, reproduced or disclosed in any form.
*/

#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include "mpi.h"

int main(int argc, char* argv[]) {
  int myRank, numProcs;

  MPI_Init(&argc,&argv);

  MPI_Comm_rank(MPI_COMM_WORLD, &myRank);
  MPI_Comm_size(MPI_COMM_WORLD, &numProcs);

  fprintf(stderr, "Hello World! from process %d\n", myRank);

  MPI_Finalize();

  return 0;
}
