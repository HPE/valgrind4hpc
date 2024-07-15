% valgrind4hpc(1)
% Hewlett Packard Enterprise Development LP
% 2018-10-08

<!--
We generate the man and html documentation page from this markdown file using pandoc.

Lines beginning with % are pandoc comments.

The comments at the top are special and will fill in that information in the generated man page.
-->

# NAME

**Valgrind4hpc**

# SYNOPSIS

valgrind4hpc **[VALGRIND4HPC OPTIONS]** [-n *number of ranks* ] *executable* [\-- **[EXECUTABLE ARGUMENTS]**]

# DESCRIPTION

**Valgrind4hpc** is a Valgrind-based debugging tool to aid in the
detection of memory leaks and errors in parallel applications.
Valgrind4hpc aggregates any duplicate messages across ranks to help
provide an understandable picture of program behavior. Valgrind4hpc
manages starting and redirecting output from many copies of Valgrind, as
well as deduplicating and filtering Valgrind messages. If your program
can be debugged with Valgrind, it can be debugged with Valgrind4hpc.

# OPTIONS

<!-- two trailing spaces added on each title to preserve line breaks -->

**-n**, **\--num-ranks**=*RANKS*  
Run with this number of ranks (default 1)

**-t**, **\--tool**=*TOOL*  
Run memcheck, helgrind, or drd with this tool on the
backend (default is memcheck)

**-l**, **\--launcher-args**=*\"arguments\"*  
arguments to the application launcher (WLM-specific)

**-i**, **\--inputfile**=*FILE*  
Use file as input to all ranks

**-o**, **\--outputfile**=*FILE*  
Specify an output file

**-s**, **\--suppressions**=*FILE*  
Specify a suppression file (can specify this argument multiple times)

**\--gen-suppressions**=*[yes|no]*  
Generate Valgrind suppressions for this job run. By default, print
output to standard error at the end of the job. To specify a file,
set **\--gen-suppressions-file**.

**\--gen-suppressions-file**=*FILE*  
Write generated suppressions to this file. If **\--gen-suppressions** is
not set, this option will enable it.

**-v**, **\--valgrind-args**=*\"arguments\"*  
Specify non-Valgrind4hpc-supported Valgrind arguments such as
\--show-leak-kinds or \--leak-check. Note that certain arguments may
interfere with the functionality of Valgrind4hpc.

**-r**, **\--from-ranks**=*\<ranks>*  
Only show Valgrind output from certain ranks. Format: \"a-c,i-k\" to
show output from ranks \"a\" through \"c\" and \"i\" through \"k\".

**-g**, **\--vgdb-error**=*\<count>*  
Start VGDB mode upon encountering this number of errors. Valgrind4hpc
will print connection instructions to run on the node for the target
rank. Direct SSH access to nodes is required for interactive GDB
debugging.

**\--cray-pmi**=*OPTION*  
ALPS only: disable automatic MPI check and manually specify whether
the target application is a parallel MPI program. Note: this solves
an ALPS-specific problem and is not necessary on SLURM systems.
Possible values: {yes, no}

**-h**, **\--help**  
Display help text and exit

# EXAMPLES

To run the program **./a.out** and debug it across 32 ranks on 16 nodes
with full Valgrind leak-checking, use the command:

    valgrind4hpc -n32 --launcher-args="-N16 -j2" --valgrind-args="--track-origins=yes --leak-check=full" ./a.out -- arg1 arg2

Note that valgrind4hpc and target program arguments should be separated
by two dashes, **\--**

# FALSE NEGATIVES

Valgrind needs to know what memory-allocating functions to wrap. To this
end, Valgrind4hpc informs Valgrind which shared library symbols perform
memory-allocating functions. To function correctly, target executables
must be built dynamically and contain debug symbols. When calling the
Cray compiler, set the environment variable

    CRAYPE_LINK_TYPE=dynamic

and compile with the debug symbol flag **-g**

# VALGRIND SUPPRESSIONS

For a full guide, see the Valgrind manual section 2.5: \"Suppressing
errors\" at \<http://valgrind.org/docs/manual/valgrind_manual.pdf>.

The Valgrind option **\--gen-suppressions**=*yes* will automatically
generate a suppression file for the currently-running program. If you
would like to use this option with Valgrind4hpc, remember to pass it as
a custom Valgrind option with
**\--valgrind-args=\"\--gen-suppressions**=yes\"

When you have created your custom suppression file, you can pass it to
Valgrind4hpc with the **\--suppressions**=*filename* argument.

