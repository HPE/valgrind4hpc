#!/bin/bash

# Driver script for installing the prerequisites for valgrind4hpc
#
# sudo ./bootstrap.sh --prep
#   installs the build requirments from the OS
# install_dir=[prefix] ./boostrap.sh
#    will build is and install the package

set -e

install_dir="${install_dir=${HOME}/hpe-tools}"

reconfigure=
prep=
for arg in "$@"; do
    if [ $arg == "--prep" ]; then
	prep=1
    elif [ $arg == "--reconfigure" ]; then
	reconfigure='--reconfigure'
    else
	echo "usage $0 [--prep]"
	exit 1
    fi
done

if [ -n "$prep" ]; then
    if [ "$(whoami)" != "root" ]; then
	echo "--prep must be run as root"
	exit 1
    fi
    echo prepping
    yum install libssh2-devel boost-devel dyninst-devel pandoc
    exit
fi

if [ $(gcc --version | grep -c '\<14\.') != 1 ]; then
    source /opt/rh/gcc-toolset-14/enable
fi    

top_level="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "############################################"
echo "#      Building valgrind4hpc               #"
echo "############################################"

# we explicitly set CC/CXX here to their full paths so that the full paths are
# baked into the meson build configuration and meson doesn't use whatever gcc/g++ is
# in PATH on subsequent builds outside of runBuild.sh
#
# valgrind4hpc locates its helper binaries, filter library and suppression
# files relative to its own install prefix, so libdir/libexecdir/datadir must
# stay at the plain lib/libexec/share defaults.
export PKG_CONFIG_PATH="$install_dir/lib/cti/pkgconfig:$install_dir/lib/pkgconfig:$PKG_CONFIG_PATH"
echo pkgconfig = $PKG_CONFIG_PATH

CC=$(which gcc) CXX=$(which g++) \
  meson setup \
    -Dprefix=$install_dir \
    -Dlibdir=lib/valgrind4hpc \
    -Dlibexecdir=libexec/valgrind4hpc \
    -Ddatadir=share/valgrind4hpc \
    -Ddebug=true \
    -Doptimization=2 \
    -Db_ndebug=true \
    $reconfigure \
    "$top_level/build" "$top_level"


if [ -z "$reconfigure" ]; then

    meson compile --verbose -C "$top_level/build"

    meson test -C "$top_level/build" || true

    meson install -C "$top_level/build"
fi    

echo "############################################"
echo "#              Done with build             #"
echo "############################################"

