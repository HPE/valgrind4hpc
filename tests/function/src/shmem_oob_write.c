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
! Test name: out_of_bounds_write_all_error.c
! Purpose:   Out of bounds memeory write in shmem for valgrind to find
!
! NOTES
!    This test should fail if shmem_malloc returns a NULL pointer.
!
!*******************************************************************************/

#include <stdio.h>
#include <shmem.h>

//vector length
#define N 512

int main (void)
{
  shmem_init();
  fprintf(stderr, "Passed Init\n");
  int me = shmem_my_pe();
  int npes = shmem_n_pes();

  int i, dummy_var;

  int *vec1 = (int *)shmem_malloc(sizeof(int) * N);
  if(vec1 == NULL)
  {
    fprintf(stdout, "shmeme_malloc returned NULL, exiting...");
    shmem_finalize();
    return 1;
  }

  //dummy code
  for(i = 0; i < N+1; ++i)
  {
    dummy_var += i % 7;
    //illegal write on last itteration, as i = N
    vec1[i] = dummy_var;
  }

  //clean up
  shmem_free(vec1);
  shmem_finalize();

  return 0;
}

