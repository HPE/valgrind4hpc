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
! Test name: sanity_check.c
! Purpose:   Basic sanity check for mpi valgrind test cases
!
! NOTES
!    This test should fail if configuration is broken or major regression.
!    If this test fails, expect all other mpi test cases to also fail.
!
!*******************************************************************************/

#include <mpi.h>
#include <stdio.h>

int main(int argc, char **argv)
{
  MPI_Init(&argc, &argv);
  fprintf(stderr, "Passed Init\n");

  int i, dummy_var = -13;

  //dummy code
  for(i = 0; i < 100; ++i)
  {
    dummy_var += i % 7;
  }

  MPI_Finalize();
  return 0;
}

