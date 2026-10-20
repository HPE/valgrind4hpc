/***********************************************************************
!*
!* Copyright 2018,2020 Hewlett Packard Enterprise Development LP.
!* Unpublished Proprietary Information.  
!* This unpublished work is protected to trade secret,
!* copyright and other laws.  Except as permitted by contract or
!* express written permission of Hewlett Packard Enterprise Development LP., no part of this work
!* or its content may be used, reproduced or disclosed in any form.
!*
!**********************************************************************
!*
!* Author       : Evan Dye, Emory University
!* Date written : 09/07/2018
!*
!*********************************************************************
!******************************************************************************
! Test name: sanity_check.c
! Purpose:   Basic sanity check for shmem valgrind test cases
!
! NOTES
!    This test should fail if configuration is broken or major regression.
!    If this test fails, expect all other shmem test cases to also fail.
!
!*******************************************************************************/

#include <shmem.h>
#include <stdio.h>

int main (int argc, char** argv)
{
  shmem_init();
  fprintf(stderr, "Passed Init\n");
  int me = shmem_my_pe();
  int npes = shmem_n_pes();

  int i, dummy_var;

  //dummy code
  for(i = 0; i < 100; ++i)
  {
    dummy_var += i % 7;
  }

  shmem_finalize();
  return 0;
}

