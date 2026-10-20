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
! Test name: illegal_free_all_error_05.c
! Purpose:   Double free in mpi for valgrind to find
!
! NOTES
!    This test should fail with illegal free
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

  int vec1[N];

  //dummy code
  for(i = 0; i < N; ++i)
  {
    dummy_var += i % 7;
    vec1[i] = dummy_var = -13;
  }

  //illegal call to free
  free(vec1);

  MPI_Finalize();
  return 0;
}

