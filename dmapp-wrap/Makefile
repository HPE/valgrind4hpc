# run with LD_PRELOAD=<path/to/dmapp-wrap.so> srun --export=LD_PRELOAD,PATH valgrind <target_program>

all: dmapp-wrap.so

VALGRIND_SRCDIR  := ../valgrind/
VALGRIND_INCDIR   := $(VALGRIND_SRCDIR)/include/
MEMCHECK_INCDIR   := $(VALGRIND_SRCDIR)/memcheck/
MEMCHECK_INCLUDES := -I$(VALGRIND_INCDIR) -I$(MEMCHECK_INCDIR)

GNI_INCDIR     := /opt/cray/gni-headers/default/include/
DMAPP_INCDIR   := /opt/cray/dmapp/default/include/
SHMEM_INCDIR   := $(CRAY_SHMEM_DIR)/include/
DMAPP_INCLUDES := -I$(GNI_INCDIR) -I$(DMAPP_INCDIR) -I$(SHMEM_INCDIR)

# only compile the UDREG wrappers if the UDREG headers are available
UDREG_INCDIR   := /opt/cray/udreg/default/include/
ifneq ("$(wildcard $(UDREG_INCDIR))","")
UDREG_INCLUDES := -I$(UDREG_INCDIR)
UDREG_WRAP_OBJ := udreg-wrap.o
else
UDREG_INCLUDES :=
UDREG_WRAP_OBJ :=
endif

all: dmapp-wrap.so

dmapp-wrap.o: dmapp-wrap.c memcheck-common.h
	gcc -c dmapp-wrap.c $(MEMCHECK_INCLUDES) $(DMAPP_INCLUDES) -g -fPIC -o dmapp-wrap.o

udreg-wrap.o: udreg-wrap.c memcheck-common.h
	gcc -c udreg-wrap.c $(MEMCHECK_INCLUDES) $(UDREG_INCLUDES) -g -fPIC -o udreg-wrap.o

dmapp-wrap.so: dmapp-wrap.o $(UDREG_WRAP_OBJ)
	gcc dmapp-wrap.o $(UDREG_WRAP_OBJ) -g -fPIC -shared -o dmapp-wrap.so

clean:
	rm -f *.so *.o