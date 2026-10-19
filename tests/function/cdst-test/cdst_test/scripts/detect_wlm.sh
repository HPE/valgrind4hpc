#!/bin/bash

if [[ "$CTI_WLM_IMPL" == localhost ]]
then
    echo "LOCALHOST"
    exit 0
fi

if [[ ! -z $CRAY_ENABLE_PE ]]
then
    source $CRAY_ENABLE_PE
fi

if [[ ! -z $(which srun 2> /dev/null) ]]
then
    echo "SLURM"
    exit 0
fi

if [[ ! -z $(which palscmd 2> /dev/null) ]]
then
    echo "PALS"
    exit 0
fi

if [[ ! -z $(which aprun 2> /dev/null) ]]
then
    echo "ALPS"
    exit 0
fi

if [[ ! -z $(which mpiexec 2> /dev/null) ]]
then
    echo "SSH"
    exit 0
fi

if [[ ! -z $(which flux 2> /dev/null) ]]
then
    echo "FLUX"
    exit 0
fi

exit -1
