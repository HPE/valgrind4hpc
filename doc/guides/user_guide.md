# valgrind4hpc User Guide

[valgrind](https://valgrind.org/) is a tool for detecting memory, threading, and other
errors in programs at runtime.

valgrind4hpc is a tool for running HPC jobs under valgrind. Using a single interface, it
launches each rank of an HPC job under the supervision of valgrind. It then collects the
results of each valgrind instance and merges them into a single report.

## A Quick Example

Let's check a multi-rank MPI app for memory leaks. One basic way to do this, without
valgrind4hpc, is to simply launch the job with a job launcher, but under the control of
valgrind.

```
$ srun -n2 valgrind --leak-check=full ./mpi_mem_leak
==37455== Memcheck, a memory error detector
==37456== Memcheck, a memory error detector
==37456== Copyright (C) 2002-2022, and GNU GPL'd, by Julian Seward et al.
==37456== Using Valgrind-3.20.0 and LibVEX; rerun with -h for copyright info
==37456== Command: ./mpi_mem_leak
==37456==
==37455== Copyright (C) 2002-2022, and GNU GPL'd, by Julian Seward et al.
==37455== Using Valgrind-3.20.0 and LibVEX; rerun with -h for copyright info
==37455== Command: ./mpi_mem_leak
==37455==
==37455==
==37456==
==37456== HEAP SUMMARY:
==37456==     in use at exit: 126,889 bytes in 597 blocks
==37456==   total heap usage: 846 allocs, 249 frees, 2,039,125 bytes allocated
==37456==
==37455== HEAP SUMMARY:
==37455==     in use at exit: 124,841 bytes in 596 blocks
==37455==   total heap usage: 859 allocs, 263 frees, 2,043,501 bytes allocated
==37455==
==37456== 2,048 bytes in 1 blocks are definitely lost in loss record 595 of 597
==37455== LEAK SUMMARY:
==37455==    definitely lost: 0 bytes in 0 blocks
==37455==    indirectly lost: 0 bytes in 0 blocks
==37455==      possibly lost: 0 bytes in 0 blocks
==37455==    still reachable: 124,841 bytes in 596 blocks
==37455==         suppressed: 0 bytes in 0 blocks
==37455== Reachable blocks (those to which a pointer was found) are not shown.
==37455== To see them, rerun with: --leak-check=full --show-leak-kinds=all
==37455==
==37455== For lists of detected and suppressed errors, rerun with: -s
==37455== ERROR SUMMARY: 0 errors from 0 contexts (suppressed: 0 from 0)
==37456==    at 0x403468B: malloc (vg_replace_malloc.c:393)
==37456==    by 0x201BBA: main (mpi_mem_leak.c:41)
==37456==
==37456== LEAK SUMMARY:
==37456==    definitely lost: 2,048 bytes in 1 blocks
==37456==    indirectly lost: 0 bytes in 0 blocks
==37456==      possibly lost: 0 bytes in 0 blocks
==37456==    still reachable: 124,841 bytes in 596 blocks
==37456==         suppressed: 0 bytes in 0 blocks
==37456== Reachable blocks (those to which a pointer was found) are not shown.
==37456== To see them, rerun with: --leak-check=full --show-leak-kinds=all
==37456==
==37456== For lists of detected and suppressed errors, rerun with: -s
==37456== ERROR SUMMARY: 1 errors from 1 contexts (suppressed: 0 from 0)
```

With only two ranks, the valgrind output is already huge. One can imagine that it would
only get worse with 20, 200, or 2000 ranks.

Taking some time to digest the valgrind output, one can see that it indicates a memory
leak. After taking even more time to sift through it, one can notice that the memory leak
is only on one rank, but the output has no indication of which one.

These are the problems that valgrind4hpc solves. Even with 64 ranks, the output is short
and indicates exactly where the memory leak is, including the offending rank. The reports
of the other non-leaky ranks are all grouped together into one output section.

```
$ valgrind4hpc -n 64 --valgrind-args="--leak-check=full" ./mpi_mem_leak

RANKS: <1>

2,048 bytes in 1 blocks are definitely lost
  at malloc (in vg_replace_malloc.c:393)
  by main (in mpi_mem_leak.c:41)


RANKS: <0,2..63>

HEAP SUMMARY:
  in use at exit: 0 bytes in 0 blocks

All heap blocks were freed -- no leaks are possible


RANKS: <1>

HEAP SUMMARY:
  in use at exit: 2048 bytes in 1 blocks

LEAK SUMMARY:
   definitely lost: 2048 bytes in 1 blocks
   indirectly lost: 0 bytes in 0 blocks
     possibly lost: 0 bytes in 0 blocks
   still reachable: 0 bytes in 0 blocks

ERROR SUMMARY: 0 errors from 0 contexts (suppressed 595)
```

Now we can clearly see that the offending rank is number 1 and the rest of the ranks are
fine.

## More Complex Job Launches and Options

valgrind4hpc has options that offer more control over the job launch and the resulting
output.

### `--`: Pass Arguments to the Application

To pass arguments to the underlying application, separate the arguments with `--` and put
application command line arguments after it.

For example, an application that launches a thread for each argument on the command line:

```
$ valgrind4hpc ./helgrind_example -- my_first_thread my_second_thread
Thread 1: top of stack near 0x19698ea0; argv_string=my_first_thread
Joined with thread 1; returned value was MY_FIRST_THREAD
Thread 2: top of stack near 0x2bb91ea0; argv_string=my_second_thread
Joined with thread 2; returned value was MY_SECOND_THREAD

RANKS: <0>

HEAP SUMMARY:
  in use at exit: 0 bytes in 0 blocks

All heap blocks were freed -- no leaks are possible

ERROR SUMMARY: 0 errors from 0 contexts (suppressed 0)
```

### `--launcher-args`: Pass Arguments to the WLM

To pass WLM-specific arguments to the underlying job launcher, use `--launcher-args`.

For example, to launch 4 ranks across 2 nodes on a Slurm system:

```
$ valgrind4hpc -n4 --launcher-args="-N2" ./mpi_mem_leak
```

`squeue` shows that it did indeed use 2 nodes:

```
$ squeue
             JOBID PARTITION     NAME     USER ST       TIME  NODES NODELIST(REASON)
           1154796  allnodes valgrind     user R        0:06      2 node[0004-0005]
```

### `--from-ranks`: Filter Out Results from Certain Ranks

One can use `--from-ranks` if one is only interested in the results of a subset of a job's
ranks. The option supports syntax to specify multiple blocks of contiguous ranks.

For example, launching 10 ranks but only displaying results from 0, 1, 2 and 4.

```
$ valgrind4hpc -n10 --from-ranks=0-2,4 ./mpi_mem_leak

RANKS: <1>

2,048 bytes in 1 blocks are definitely lost
  at malloc (in vg_replace_malloc.c:393)
  by main (in mpi_mem_leak.c:41)


RANKS: <0,2,4>

HEAP SUMMARY:
  in use at exit: 0 bytes in 0 blocks

All heap blocks were freed -- no leaks are possible


RANKS: <1>

HEAP SUMMARY:
  in use at exit: 2048 bytes in 1 blocks

LEAK SUMMARY:
   definitely lost: 2048 bytes in 1 blocks
   indirectly lost: 0 bytes in 0 blocks
     possibly lost: 0 bytes in 0 blocks
   still reachable: 0 bytes in 0 blocks

ERROR SUMMARY: 0 errors from 0 contexts (suppressed 595)
```

## Using valgrind Tools Other than memcheck

While valgrind is most commonly used for detecting memory leaks, valgrind is actually the
name of the generic framework that the memory leak tool, called memcheck, is built upon.
valgrind includes other tools for detecting other kinds of errors, and valgrind4hpc
supports the usage of these extra tools.

valgrind4hpc supports valgrind tools other than memcheck with the `--tool` command line
option. For example, one can use helgrind, which detects thread programming errors.

This program has a race condition where two threads try to write to the global variable
`global`:

```
$ valgrind4hpc -n2 --tool=helgrind ./helgrind_example -- one two

RANKS: <0,1>

Possible data race during write of size 4 at 0x205144 by thread #3
  at thread_start (in helgrind_example.c:39)
  by mythread_wrapper (in hg_intercepts.c:406)
  by start_thread (in ./helgrind_example)
  by clone (in ./helgrind_example)
  by thread_start (in helgrind_example.c:39)
  by mythread_wrapper (in hg_intercepts.c:406)
  by start_thread (in ./helgrind_example)
  by clone (in ./helgrind_example)
Address is 0 bytes inside data symbol "global"

RANKS: <0,1>

HEAP SUMMARY:
  in use at exit: 0 bytes in 0 blocks

All heap blocks were freed -- no leaks are possible

ERROR SUMMARY: 1 errors from 1 contexts (suppressed 71)
```

## Suppressions

Sometimes, valgrind detects errors in e.g. a shared library that is not directly related
to the program one is debugging with valgrind at the moment. valgrind has the notion of
suppressions to remove errors that come from these locations in order to clean up the
valgrind output.

Some previous examples had a `(suppressed *)` at the end of the valgrind report. This is
because valgrind4hpc has built in suppressions that automatically filter out memory errors
in standard HPC libraries like MPI and SHMEM.

valgrind4hpc also supports custom suppression files. The format is identical to valgrind
suppression files.

If valgrind4hpc outputs an error in an external library or in a location that one would
otherwise want to suppress, one can use valgrind4hpc's `--gen-suppressions` option to
generate suppressions in the valgrind4hpc output. The generated suppressions should be
saved into a file. Alternatively, `--gen-suppressions-file=<file>` can be used to create a
suppression file in a single step.

To use suppressions, one can use the `--suppressions=<file>` argument. For multiple
suppression files, the option can be used more than once.

For example:

```
$ valgrind4hpc -n2 --gen-suppressions=yes ./mpi_mem_leak

RANKS: <1>

2,048 bytes in 1 blocks are definitely lost
  at malloc (in vg_replace_malloc.c:393)
  by main (in mpi_mem_leak.c:41)

... normal valgrind4hpc output omitted ...

GENERATED SUPPRESSIONS:

{
   <insert_a_suppression_name_here>
   Memcheck:Leak
   match-leak-kinds: definite
   fun:malloc
   fun:main
}

$ valgrind4hpc -n2 --gen-suppressions-file=leak_suppressions.txt ./mpi_mem_leak

RANKS: <1>

2,048 bytes in 1 blocks are definitely lost
  at malloc (in vg_replace_malloc.c:393)
  by main (in mpi_mem_leak.c:41)

... normal valgrind4hpc output omitted ...

$ cat ./leak_suppressions.txt

{
   <insert_a_suppression_name_here>
   Memcheck:Leak
   match-leak-kinds: definite
   fun:malloc
   fun:main
}

$ valgrind4hpc -n2 --suppressions=./leak_suppressions.txt ./mpi_mem_leak

RANKS: <0,1>

HEAP SUMMARY:
  in use at exit: 0 bytes in 0 blocks

All heap blocks were freed -- no leaks are possible

ERROR SUMMARY: 0 errors from 0 contexts (suppressed 1191)
```

## vgdb

vgdb is a way to stop valgrind after a number of errors and attach to the program under
valgrind in gdb. valgrind4hpc offers a similar workflow where the application is stopped
and can be debugged with gdb4hpc.

Use the `--vgdb` valgrind4hpc argument to have valgrind4hpc stop after a certain amount of
errors and print instructions on how to attach to the running app with gdb4hpc.

```
$ valgrind4hpc -n2 --vgdb-error=1 ./mpi_mem_leak

RANKS: <0,1>

Entered VGDB mode. To attach to with GDB4hpc: start GDB4hpc and run
  attach $a --vgdb=/tmp/cti_daemonjuWtME/vgdb-commands 1155209.0

```

In gdb4hpc:

```
$ gdb4hpc -s
dbg all> attach $a --vgdb=/tmp/cti_daemonjuWtME/vgdb-commands 1155209.0
0/2 ranks connected... (timeout in 299 seconds)
2/2 ranks connected.
Created network...
Connected to application...
Current rank location:
a{0}: #0  0x00000000082d2c8a in clock_nanosleep@GLIBC_2.2.5
a{0}: #1  0x00000000082d89e3 in nanosleep
a{0}: #2  0x00000000082d88fa in sleep
a{0}: #3  0x0000000000201c92 in main at mpi_mem_leak.c:60

a{1}: #0  0x0000000007172419 in MPIDI_SHMI_progress
a{1}: #1  0x0000000005b59a59 in MPIR_Wait_impl.part.0
a{1}: #2  0x00000000069531f6 in MPIC_Wait
a{1}: #3  0x0000000006966bbc in MPIC_Sendrecv
a{1}: #4  0x00000000068700b2 in MPIR_Barrier_intra_dissemination
a{1}: #5  0x0000000004ecabf1 in MPIR_Barrier_intra_auto
a{1}: #6  0x0000000004ecad18 in MPIR_Barrier_impl
a{1}: #7  0x0000000006b5ee0b in MPIR_CRAY_Barrier
a{1}: #8  0x0000000004ecade0 in MPIR_Barrier
a{1}: #9  0x0000000006b55362 in MPIDI_Cray_shared_mem_coll_opt_cleanup
a{1}: #10 0x0000000006998dc5 in MPIDI_Cray_coll_finalize
a{1}: #11 0x0000000006ceffbf in MPID_Finalize
a{1}: #12 0x000000000537778e in PMPI_Finalize
a{1}: #13 0x0000000000201c97 in main at mpi_mem_leak.c:63
```
