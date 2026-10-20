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
!* Date written : 10/19/2018
!*
!*********************************************************************
!******************************************************************************
! Test name: out_of_bounds_write_all_error_07.c
! Purpose:   Out of bounds memory write in mpi for valgrind to find
!
! NOTES
!    This test should fail if malloc returns a NULL pointer.
!
!*******************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>

//vector length
#define S_N 9
#define R_N 8

int main(int argc, char **argv)
{
  MPI_Init(&argc, &argv);
  fprintf(stderr, "Passed Init\n");

  int i, dummy_var = -13;
  int my_rank, nprocs, send_rank, recv_rank;
  MPI_Request s_request, r_request;
  MPI_Status status;

  //Initialize Variables
  MPI_Comm_rank(MPI_COMM_WORLD, &my_rank);
  MPI_Comm_size(MPI_COMM_WORLD, &nprocs);

  send_rank = (my_rank + 1) % nprocs;
  recv_rank = my_rank - 1;
  if(recv_rank == -1) recv_rank = nprocs-1;

  int *s_buf = (int *)malloc(sizeof(int) * S_N);
  if(s_buf == NULL)
  {
    fprintf(stdout, "malloc returned NULL, exiting...");
    MPI_Finalize();
    return 1;
  }

  int *r_buf = (int *)malloc(sizeof(int) * R_N);
  if(r_buf == NULL)
  {
    fprintf(stdout, "malloc returned NULL, exiting...");
    free(s_buf);
    MPI_Finalize();
    return 1;
  }

  //dummy code
  for(i = 0; i < S_N; ++i)
  {
    dummy_var += i % 7;
    s_buf[i] = dummy_var = -13;
  }
  for(i = 0; i < R_N; ++i)
  {
    dummy_var += i % 13;
    r_buf[i] = dummy_var = -13;
  }

  //Send/Recv non-blocking
  MPI_Isend(s_buf, S_N, MPI_INT, send_rank, 1, MPI_COMM_WORLD, &s_request);
  //Note that S_N > R_N so an illegal write will occur
  MPI_Irecv(r_buf, S_N, MPI_INT, recv_rank, 1, MPI_COMM_WORLD, &r_request);

  //Wait for send/recv to finish
  MPI_Wait(&s_request, &status);
  MPI_Wait(&r_request, &status);

  //clean up
  free(s_buf);
  free(r_buf);

  MPI_Finalize();
  return 0;
}

