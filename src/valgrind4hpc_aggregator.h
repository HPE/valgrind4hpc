/******************************************************************************\
 * valgrind4hpc_aggregator.h - Aggregation definitions.
 *
 * Copyright 2015-2017,2020 Hewlett Packard Enterprise Development LP.
 *
 * Unpublished Proprietary Information.
 * This unpublished work is protected to trade secret, copyright and other laws.
 * Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
 * no part of this work or its content may be used, reproduced or disclosed
 * in any form.
 *
 ******************************************************************************/

#ifndef _VALGRIND4HPC_AGGREGATOR_H
#define _VALGRIND4HPC_AGGREGATOR_H

#include <string>
#include <unordered_map>

#include <iostream>
#include <utility>
#include <chrono>

#include <boost/dynamic_bitset.hpp>
#include <boost/optional.hpp>

#include "valgrind4hpc_protocol.h"
#include "mrnet/Types.h"

template <typename T>
using MaybeEntry = boost::optional<std::pair<T, rank_set_t>>;

static inline void readable_ranks(std::ostream& out, rank_set_t& ranks)
{
	out << "RANKS: <";
	enum states_t { Seen_0, Seen_1, Seen_2, In_range };
	states_t state = Seen_0;
	bool printSeparator = false;
	
	for (size_t i = 0; i < ranks.size(); i++)
	{
		switch (state)
		{
		case (Seen_0):
			if (ranks[i]) {
				if (printSeparator) {
					out << ",";
				} else {
					printSeparator = true;
				}
				out << i;
				state = Seen_1;
			}
			break;

		case (Seen_1):
			state = (ranks[i]) ? Seen_2 : Seen_0;
			break;

		case (Seen_2):
			if (ranks[i]) {
				out << "..";
				printSeparator = false;
				state = In_range;
			} else {
				out << "," << i - 1;
				state = Seen_0;
			}
			break;

		case (In_range):
			if (!ranks[i]) {
				out << i - 1;
				state = Seen_0;
				printSeparator = true;
			}
			break;
		};
	}

	// print last rank if suppressed in range
	if ((state != Seen_1) && ranks[ranks.size() - 1]) {
		if (printSeparator) { out << ","; }
		out << ranks.size() - 1;
	}

	out << ">" << std::endl;

	return;
}

// Our abstract aggregator class
template <typename T>
class Aggregator
{
public:
	using EntryMap = std::unordered_map<T, rank_set_t>;

protected:
	rank_set_t target_bitset;
	EntryMap entries;
public:
	Aggregator(rank_set_t target_bitset_)
		: target_bitset{target_bitset_}
		, entries{target_bitset.count()}
	{}
	virtual ~Aggregator() = default;

	typename EntryMap::iterator begin() { return entries.begin(); }
	typename EntryMap::iterator end()   { return entries.end(); }
	size_t size() const { return entries.size(); }

	virtual MaybeEntry<T> update(T&, int, bool final = false) = 0;
	virtual MaybeEntry<T> merge(T&, rank_set_t&) = 0;
	virtual MaybeEntry<T> evict() = 0;
};

template <typename T>
static inline auto find_or_create_bitset(std::unordered_map<T, rank_set_t>& entries,
	T const& obj, size_t new_bitset_size)
{
	// Find bitset for obj's entry
	auto bs_it = entries.find(obj);
	if (bs_it == entries.end()) {

		// Create new empty bitset for obj
		auto bs = rank_set_t{};
		bs.resize(new_bitset_size);
		auto&& new_bs_it = entries.emplace(obj, std::move(bs)).first;
		return &new_bs_it->second;

	} else {
		return &bs_it->second;
	}
}

static inline auto safe_equals(rank_set_t const& rhs, rank_set_t const& lhs)
{
	if (rhs.size() == lhs.size()) {
		return rhs == lhs;
	}

	auto& smaller = (lhs.size() < rhs.size()) ? lhs : rhs;
	auto& larger = (lhs.size() < rhs.size()) ? rhs : lhs;

	for (size_t i = 0; i < smaller.size(); i++) {
		if (lhs[i] != rhs[i]) {
			return false;
		}
	}

	for (size_t i = smaller.size(); i < larger.size(); i++) {
		if (larger[i]) {
			return false;
		}
	}

	return true;
}

static inline auto safe_intersection(rank_set_t const& lhs, rank_set_t const& rhs)
{
	auto const min_size = std::min(lhs.size(), rhs.size());
	for (size_t i = 0; i < min_size; i++) {
		if (lhs[i] && rhs[i]) {
			return true;
		}
	}

	return false;
}

static inline auto safe_test(rank_set_t const& bitset, size_t n)
{
	return (n < bitset.size()) ? bitset.test(n) : false;
}

static inline void safe_set(rank_set_t& bitset, size_t n)
{
	if (bitset.size() <= n) {
		bitset.resize(n + 1, true);
	} else {
		bitset.set(n);
	}
}

static inline void safe_or(rank_set_t& lhs, rank_set_t const& rhs)
{
	if (lhs.size() == rhs.size()) {
		lhs |= rhs;

	} else if (lhs.size() < rhs.size()) {
		lhs.resize(rhs.size());
		lhs |= rhs;

	} else if (lhs.size() > rhs.size()) {
		for (size_t i = 0; i < rhs.size(); i++) {
			lhs[i] = lhs[i] | rhs[i];
		}
	}
}

static inline void safe_and(rank_set_t& lhs, rank_set_t const& rhs)
{
	throw std::runtime_error("safe_and");
	if (lhs.size() != rhs.size()) {
		lhs.resize(rhs.size());
	}
	lhs &= rhs;
}


/* FullAggregator updates which blocks have been seen from which rank, and evicts blocks that have
	been received from all ranks.
*/
template <class T>
class FullAggregator : public Aggregator<T>
{
public:
	FullAggregator(rank_set_t target_bitset) : Aggregator<T>(target_bitset) {}
	~FullAggregator() = default;

	MaybeEntry<T> evict() {
		return boost::none;
	}

	MaybeEntry<T> update(T& obj, int rank, bool final = false) {

		// Test against target bitset
		if (!safe_test(this->target_bitset, rank)) {
			return boost::none;
		}

		// Find bitset for obj's entry
		auto bs = find_or_create_bitset(this->entries, obj,
			this->target_bitset.size());

		// Set rank in bitset for obj
		safe_set(*bs, rank);

		// Check to see if obj has reported from all ranks
		if (safe_equals(*bs, this->target_bitset) || final) {
			auto evicted = std::make_pair(obj, *bs);
			this->entries.erase(obj);
			return evicted;
		}

		return boost::none;
	}

	MaybeEntry<T> merge(T& obj, rank_set_t& other) {

		// Test against target bitset
		if (!safe_intersection(this->target_bitset, other)) {
			return boost::none;
		}

		// Find bitset for obj's entry
		auto bs = find_or_create_bitset(this->entries, obj,
			this->target_bitset.size());

		// Merge active subset with obj's ranks
		safe_or(*bs, other);

		// Check to see if obj has reported from all ranks
		if (safe_equals(*bs, this->target_bitset)) {
			auto evicted = std::make_pair(obj, *bs);
			this->entries.erase(obj);
			return evicted;
		}

		return boost::none;
	}
};

/* FilterAggregator is used in MRNet reduction to merge blocks by bitset.
	As MRNet reduction occurs between backend and frontend, this aggregator is not expected to
	provide an update or an evict function (responsibilities of backend / frontend).
*/
template <class T>
class FilterAggregator final : public Aggregator<T>
{
public:
	FilterAggregator() : Aggregator<T>({}) { }
	~FilterAggregator() = default;

	MaybeEntry<T> update(T&, int, bool final = false) {
		return boost::none;
	}
	MaybeEntry<T> evict() {
		return boost::none;
	}

	MaybeEntry<T> merge(T& obj, rank_set_t& other) {

		// Find bitset for obj's entry
		auto bs = find_or_create_bitset(this->entries, obj,
			this->target_bitset.size());

		// Merge bitsets
		safe_or(*bs, other);

		return boost::none;
	}
};

/* FullTimerAggregator performs full aggregation, but also evicts blocks that are older than
	a timeout value.
*/
template <class T>
class FullTimerAggregator : public Aggregator<T>
{
protected:
	std::map<std::chrono::steady_clock::time_point, T> arrival_times;
	double seconds;

public:
	FullTimerAggregator(double s, rank_set_t target_bitset)
		: Aggregator<T>(target_bitset)
		, seconds(s)
	{}
	~FullTimerAggregator() = default;

	MaybeEntry<T> update(T& obj, int rank, bool final = false) {

		// Test against target bitset
		if (!safe_test(this->target_bitset, rank)) {
			return boost::none;
		}

		// Find bitset for obj's entry
		auto bs = find_or_create_bitset(this->entries, obj,
			this->target_bitset.size());

		// Set rank in bitset for obj
		safe_set(*bs, rank);

		// Check to see if obj has reported from all ranks
		if (safe_equals(*bs, this->target_bitset) || final) {
			auto evicted = std::make_pair(obj, *bs);
			this->entries.erase(obj);
			return evicted;
		}

		return boost::none; 
	}

	MaybeEntry<T> merge(T& obj, rank_set_t& other) {

		// Test against target bitset
		if (!safe_intersection(this->target_bitset, other)) {
			return boost::none;
		}

		// Find bitset for obj's entry
		auto bs = find_or_create_bitset(this->entries, obj,
			this->target_bitset.size());

		// Merge bitsets
		safe_or(*bs, other);

		// Check to see if obj has reported from all ranks
		if (safe_equals(*bs, this->target_bitset)) {
			auto evicted = std::make_pair(obj, *bs);
			this->entries.erase(obj);
			return evicted;
		}

		return boost::none;
	}

	MaybeEntry<T> evict() {

		auto time_it = arrival_times.begin();
		while (time_it != arrival_times.end()){
			auto obj = time_it->second;
			auto time = time_it->first;
			auto bs_it = this->entries.find(obj);
			if(bs_it == this->entries.end()){
				time_it++;
				arrival_times.erase(time);
				continue;
			}
			rank_set_t * bs = &bs_it->second;
			std::chrono::duration<double> time_spent = std::chrono::steady_clock::now() - time;
			if(safe_equals(*bs, this->target_bitset) || time_spent.count() > seconds){
				std::pair<T, rank_set_t> evicted = std::make_pair(obj,* bs);
				this->entries.erase(obj);
				arrival_times.erase(time);
				return evicted;
			}
			time_it++;
		}
		return boost::none;
	}
};

/* NoEvictAggregator uses the same aggregation scheme as FullAggregator, but does not evict
	blocks with all ranks set. Manually output all blocks using range-based .begin() / .end()
	accessors implemented in base Aggregator<T>.
	Manual eviction means that usage should be limited. Currently used to delay summary block
	outputs until end of run (one summary block per rank kept in this aggregator is acceptable).
*/
template <class T>
class NoEvictAggregator : public Aggregator<T>
{
public:
	NoEvictAggregator(rank_set_t& target_bitset) : Aggregator<T>(target_bitset) { }
	~NoEvictAggregator() = default;

	MaybeEntry<T> evict() {
		return boost::none;
	}

	MaybeEntry<T> update(T& obj, int rank, bool final = false) {

		// Test against target bitset
		if (!safe_test(this->target_bitset, rank)) {
			return boost::none;
		}

		// Find bitset for obj's entry
		auto bs = find_or_create_bitset(this->entries, obj,
			this->target_bitset.size());

		// Set rank in bitset for obj
		safe_set(*bs, rank);

		// Check to see if obj has reported from all ranks
		if (safe_equals(*bs, this->target_bitset) || final) {
			auto evicted = std::make_pair(obj, *bs);
			this->entries.erase(obj);
			return evicted;
		}

		return boost::none;
	}

	MaybeEntry<T> merge(T& obj, rank_set_t& other) {

		// Test against target bitset
		if (!safe_intersection(this->target_bitset, other)) {
			return boost::none;
		}

		// Find bitset for obj's entry
		auto bs = find_or_create_bitset(this->entries, obj,
			this->target_bitset.size());

		// Merge bitsets
		safe_or(*bs, other);

		return boost::none;
	}
};

#endif /* _APGRIND_AGGREGATOR_H */
