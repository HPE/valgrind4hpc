/******************************************************************************\
 * memcheck-common.h - Valgrind Memcheck helper functions for DMAPP and UDREG wrappers
 *
 * Copyright 2015-2018,2020 Hewlett Packard Enterprise Development LP.
 *
 * Unpublished Proprietary Information.
 * This unpublished work is protected to trade secret, copyright and other laws.
 * Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
 * no part of this work or its content may be used, reproduced or disclosed
 * in any form.
 *
 ******************************************************************************/

#include <stdio.h>
#include <unistd.h>

#include <valgrind.h>
#include <memcheck.h>

/* library debugging */
#ifdef DEBUG

// debug variables
static int   initialized = 0;
static pid_t my_pid      = -1;

// debug output
#define debug_print(fmt, ...) \
do { fprintf(stderr, "dmapp-wrap %5d: " fmt, my_pid, __VA_ARGS__); } while (0)

inline static void before(const char* fnname) {
	if (!initialized) {
		my_pid = getpid();
		debug_print("active from %s\n", fnname);
		initialized = 1;
	}
	debug_print("enter %s\n", fnname);
}

inline static void after(const char* fnname) {
	debug_print("exit %s\n", fnname);
}

#else // ifndef DEBUG

#define debug_print(fmt, ...)
inline static void before(const char* ignored) { }
inline static void after(const char* ignored)  { }

#endif // ifdef DEBUG

/* memcheck macro wrappers */

inline static void vg_make_defined(const char* start, size_t len) {
	// debug_print("defined %p - %p\n", start, start + len);
	VALGRIND_MAKE_MEM_DEFINED(start, len);
}

inline static void vg_make_undefined(const char* start, size_t len) {
	debug_print("undefined %p - %p\n", start, start + len);
	VALGRIND_MAKE_MEM_UNDEFINED(start, len);
}

inline static void vg_make_noaccess(const char* start, size_t len) {
	debug_print("noaccess %p - %p\n", start, start + len);
	VALGRIND_MAKE_MEM_NOACCESS(start, len);
}

inline static void vg_create_mempool(const char* pool, size_t redzone_size, int is_zeroed) {
	debug_print("create mempool %p\n", pool);
	VALGRIND_CREATE_MEMPOOL(pool, redzone_size, is_zeroed);
}

inline static int vg_mempool_alloc(const char* pool, const char* buffer, size_t len) {
	debug_print("mempool alloc (%p, 0x%x) in %p\n", buffer, len, pool);
	VALGRIND_MEMPOOL_ALLOC(pool, buffer, len);
}

inline static int vg_mempool_free(const char* pool, const char* buffer) {
	debug_print("mempool free (%p) from %p\n", buffer, pool);
	VALGRIND_MEMPOOL_FREE(pool, buffer);
}

inline static int vg_mempool_exists(const char* pool) {
	// debug_print("mempool exists %p\n", pool);
	return VALGRIND_MEMPOOL_EXISTS(pool);
}

inline static void vg_disable_reporting(const char* start, size_t len) {
	// debug_print("disable %p - %p\n", start, start + len);
	VALGRIND_DISABLE_ADDR_ERROR_REPORTING_IN_RANGE(start, start + len);
}

inline static void vg_enable_reporting(const char* start, size_t len) {
	// debug_print("enable %p - %p\n", start, start + len);
	VALGRIND_ENABLE_ADDR_ERROR_REPORTING_IN_RANGE(start, start + len);
}

inline static int vg_addressable(const char* start, size_t len) {
	debug_print("check addressable %p - %p\n", start, start + len);
	return !VALGRIND_CHECK_MEM_IS_ADDRESSABLE(start, len);
}

inline static int vg_defined(const char* start, size_t len) {
	debug_print("check defined %p - %p\n", start, start + len);
	return !VALGRIND_CHECK_MEM_IS_DEFINED(start, len);
}

inline static int vg_malloclike(const char* buffer, size_t len) {
	debug_print("malloclike (%p, 0x%x)\n", buffer, len);
	VALGRIND_MALLOCLIKE_BLOCK(buffer, len, 0, 0);
}

inline static int vg_freelike(const char* buffer) {
	debug_print("malloclike (%p)\n", buffer);
	VALGRIND_FREELIKE_BLOCK(buffer, 0);
}
