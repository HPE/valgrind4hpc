/******************************************************************************\
 * dmapp-wrap.c - DMAPP wrappers for Valgrind Memcheck
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

#include "memcheck-common.h"

#include <dmapp.h>

dmapp_jobinfo_t job_info;

/* pool management */

static void register_segment_as_pool(const dmapp_seg_desc_t* segment) {
	// establish new blocks as valgrind mempools
	const char*  seg_pool     = segment->addr;
	const size_t redzone_size = 0;
	const int    is_zeroed    = 0;
	vg_create_mempool(seg_pool, redzone_size, is_zeroed);

	// mark symmetric heap as noaccess
	const size_t sheap_size = segment->len;
	vg_make_noaccess(seg_pool, sheap_size);
}

static const char* get_pool(const dmapp_seg_desc_t* segment) {
	const char* seg_pool = segment->addr;

	// register segment as pool with valgrind if needed
	if (!vg_mempool_exists(seg_pool)) {
		register_segment_as_pool(segment);
	}

	return seg_pool;
}

/* dmapp wrappers */

#define DMAPP_WRAPPER(name) I_WRAP_SONAME_FNNAME_ZU(libdmappZaZdsoZa,name)

dmapp_return_t DMAPP_WRAPPER(dmapp_init_ext)(dmapp_rma_attrs_ext_t *requested_attrs,
	dmapp_rma_attrs_ext_t *actual_attrs) {

	OrigFn fn;
	VALGRIND_GET_ORIG_FN(fn);
	before("dmapp_init_ext");

	// make call
	dmapp_return_t init_result; // enum int
	CALL_FN_W_WW(init_result, fn, requested_attrs, actual_attrs);

	// register dmapp segments as pools
	dmapp_get_jobinfo(&job_info);
	if (!vg_mempool_exists(job_info.sheap_seg.addr)) {
		register_segment_as_pool(&job_info.sheap_seg);
	}

	after("dmapp_init_ext");
	return init_result;
}

static void* dmapp_generic_malloc(OrigFn fn, size_t buf_size, dmapp_seg_desc_t *segment) {
	// make call without reporting
	void *buffer = NULL;
	vg_disable_reporting(segment->addr, segment->len);
	CALL_FN_W_WW(buffer, fn, buf_size, segment);
	vg_enable_reporting(segment->addr, segment->len);

	// allocate block in segment pool
	const char* seg_pool    = get_pool(segment);
	const char* dmapp_block = (char*)buffer;
	vg_mempool_alloc(seg_pool, dmapp_block, buf_size);

	return buffer;
}

void* DMAPP_WRAPPER(dmapp_user_sheap_malloc)(size_t buf_size, dmapp_seg_desc_t *segment) {
	OrigFn fn;
	VALGRIND_GET_ORIG_FN(fn);
	before("dmapp_user_sheap_malloc");

	void *buffer = dmapp_generic_malloc(fn, buf_size, segment);

	after("dmapp_user_sheap_malloc");
	return buffer;
}

void DMAPP_WRAPPER(dmapp_user_sheap_free)(void* buffer, dmapp_seg_desc_t *segment) {
	OrigFn fn;
	VALGRIND_GET_ORIG_FN(fn);
	before("dmapp_user_sheap_free");

	// make call without reporting
	vg_disable_reporting(segment->addr, segment->len);
	CALL_FN_v_WW(fn, buffer, segment);
	vg_enable_reporting(segment->addr, segment->len);

	// free block from segment pool
	const char* seg_pool    = get_pool(segment);
	const char* dmapp_block = (char*)buffer;
	vg_mempool_free(seg_pool, dmapp_block);

	after("dmapp_user_sheap_free");
	return;
}

/* dmapp_put */

static size_t dmapp_sizeof(uint64_t nelems, dmapp_type_t type) {
	switch (type) {
		case DMAPP_DQW:  return 16 * nelems;
		case DMAPP_QW:   return  8 * nelems;
		case DMAPP_DW:   return  4 * nelems;
		case DMAPP_BYTE: return  1 * nelems;
		default:         return  0;
	}
}

dmapp_return_t DMAPP_WRAPPER(dmapp_put)(void *target_addr, dmapp_seg_desc_t *target_seg,
	dmapp_pe_t target_pe, void *source_addr, uint64_t nelems, dmapp_type_t type) {

	OrigFn fn;
	VALGRIND_GET_ORIG_FN(fn);

	// make call
	dmapp_return_t result;
	CALL_FN_W_6W(result, fn, target_addr, target_seg, target_pe, source_addr, nelems, type);

	// make region defined
	vg_make_defined(target_addr, dmapp_sizeof(nelems, type));

	return result;
}

dmapp_return_t DMAPP_WRAPPER(dmapp_put_nb)(void *target_addr, dmapp_seg_desc_t *target_seg,
	dmapp_pe_t target_pe, void *source_addr, uint64_t nelems, dmapp_type_t type,
	dmapp_syncid_handle_t *syncid) {

	OrigFn fn;
	VALGRIND_GET_ORIG_FN(fn);

	// make call
	dmapp_return_t result;
	CALL_FN_W_7W(result, fn, target_addr, target_seg, target_pe, source_addr, nelems, type, syncid);

	// make region defined
	vg_make_defined(target_addr, dmapp_sizeof(nelems, type));

	return result;
}

dmapp_return_t DMAPP_WRAPPER(dmapp_put_nbi)(void *target_addr, dmapp_seg_desc_t *target_seg,
	dmapp_pe_t target_pe, void *source_addr, uint64_t nelems, dmapp_type_t type) {

	OrigFn fn;
	VALGRIND_GET_ORIG_FN(fn);

	// make call
	dmapp_return_t result;
	CALL_FN_W_6W(result, fn, target_addr, target_seg, target_pe, source_addr, nelems, type);

	// make region defined
	vg_make_defined(target_addr, dmapp_sizeof(nelems, type));

	return result;
}

#ifdef dmapp_ctx_t

dmapp_return_t DMAPP_WRAPPER(dmapp_ctx_put_nb)(void *target_addr, dmapp_seg_desc_t *target_seg,
	dmapp_pe_t target_pe, void *source_addr, uint64_t nelems, dmapp_type_t type, dmapp_ctx_t ctx,
	dmapp_syncid_handle_t *syncid) {

	OrigFn fn;
	VALGRIND_GET_ORIG_FN(fn);

	// make call
	dmapp_return_t result;
	CALL_FN_W_8W(result, fn, target_addr, target_seg, target_pe, source_addr, nelems, type, ctx, syncid);

	// make region defined
	vg_make_defined(target_addr, dmapp_sizeof(nelems, type));

	return result;
}

dmapp_return_t DMAPP_WRAPPER(dmapp_ctx_put_nbi)(void *target_addr, dmapp_seg_desc_t *target_seg,
	dmapp_pe_t target_pe, void *source_addr, uint64_t nelems, dmapp_type_t type, dmapp_ctx_t ctx) {

	OrigFn fn;
	VALGRIND_GET_ORIG_FN(fn);

	// make call
	dmapp_return_t result;
	CALL_FN_W_7W(result, fn, target_addr, target_seg, target_pe, source_addr, nelems, type, ctx);

	// make region defined
	vg_make_defined(target_addr, dmapp_sizeof(nelems, type));

	return result;
}

dmapp_return_t DMAPP_WRAPPER(dmapp_ctx_put)(void *target_addr, dmapp_seg_desc_t *target_seg,
	dmapp_pe_t target_pe, void *source_addr, uint64_t nelems, dmapp_type_t type, dmapp_ctx_t ctx) {

	OrigFn fn;
	VALGRIND_GET_ORIG_FN(fn);

	// make call
	dmapp_return_t result;
	CALL_FN_W_7W(result, fn, target_addr, target_seg, target_pe, source_addr, nelems, type, ctx);

	// make region defined
	vg_make_defined(target_addr, dmapp_sizeof(nelems, type));

	return result;
}

#endif

/* dmapp_get */

dmapp_return_t DMAPP_WRAPPER(dmapp_get)(void *target_addr, void *source_addr,
	dmapp_seg_desc_t *source_seg, dmapp_pe_t source_pe, uint64_t nelems, dmapp_type_t type,
	dmapp_syncid_handle_t *syncid) {

	OrigFn fn;
	VALGRIND_GET_ORIG_FN(fn);

	// make call
	dmapp_return_t result;
	CALL_FN_W_7W(result, fn, target_addr, source_addr, source_seg, source_pe, nelems, type, syncid);

	// make region defined
	vg_make_defined(target_addr, dmapp_sizeof(nelems, type));

	return result;
}

dmapp_return_t DMAPP_WRAPPER(dmapp_get_nbi)(void *target_addr, void *source_addr,
	dmapp_seg_desc_t *source_seg, dmapp_pe_t source_pe, uint64_t nelems, dmapp_type_t type) {

	OrigFn fn;
	VALGRIND_GET_ORIG_FN(fn);

	// make call
	dmapp_return_t result;
	CALL_FN_W_6W(result, fn, target_addr, source_addr, source_seg, source_pe, nelems, type);

	// make region defined
	vg_make_defined(target_addr, dmapp_sizeof(nelems, type));

	return result;
}

dmapp_return_t DMAPP_WRAPPER(dmapp_get_flag_nbi)(void *target_addr, void *source_addr,
	dmapp_seg_desc_t *source_seg, dmapp_pe_t source_pe, uint64_t nelems, dmapp_type_t type) {

	OrigFn fn;
	VALGRIND_GET_ORIG_FN(fn);

	// make call
	dmapp_return_t result;
	CALL_FN_W_6W(result, fn, target_addr, source_addr, source_seg, source_pe, nelems, type);

	// make region defined
	vg_make_defined(target_addr, dmapp_sizeof(nelems, type));

	return result;
}
