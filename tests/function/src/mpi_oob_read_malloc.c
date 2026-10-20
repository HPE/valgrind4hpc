/***********************************************************************
!*
!* 2018 Cray Inc.  All Rights Reserved.  Unpublished Proprietary
!* Information.  This unpublished work is protected to trade secret,
!* copyright and other laws.  Except as permitted by contract or
!* express written permission of Cray Inc., no part of this work
!* or its content may be used, reproduced or disclosed in any form.
!*
!**********************************************************************
!*
!* Author       : Evan Dye, Emory University
!* Date written : 10/05/2018
!*
!*********************************************************************
!******************************************************************************
! Test name: out_of_bounds_read_all_error_01.c
! Purpose:   Out of bounds memeory read in mpi for valgrind to find
!
! NOTES
!    This test should fail if malloc returns a NULL pointer.
!
!*******************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>

//vector length
#define N 512

int main(int argc, char **argv)
{
  MPI_Init(&argc, &argv);
  fprintf(stderr, "Passed Init\n");

  int i, dummy_var = -13;

  int *vec1 = (int *)malloc(sizeof(int) * N);
  if(vec1 == NULL)
  {
    fprintf(stdout, "malloc returned NULL, exiting...");
    MPI_Finalize();
    return 1;
  }

  //dummy code
  for(i = 0; i < N; ++i)
  {
    dummy_var += i % 7;
    vec1[i] = dummy_var = -13;
  }
  //illegal read, as i = N
  dummy_var = vec1[N];

  //clean up
  free(vec1);

  MPI_Finalize();
  return 0;
}

