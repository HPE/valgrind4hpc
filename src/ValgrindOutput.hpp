/******************************************************************************\
 * ValgrindOutput.hpp - Valgrind error block output object
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

#ifndef VALGRINDOUTPUT_HPP_
#define VALGRINDOUTPUT_HPP_

#include <unordered_map>

#include <boost/optional.hpp>
#include <boost/foreach.hpp>
#include <boost/property_tree/ptree.hpp>

#include "utils/TSQueue.hpp"

#include "valgrind4hpc_defs.h"
#include "valgrind4hpc_protocol.h"
#include "valgrind4hpc_BE.h"

// Valgrind XML format: see https://github.com/svn2github/valgrind/blob/master/docs/internals/xml-output-protocol4.txt

using Ptree = boost::property_tree::ptree;
using PtreeVal = boost::property_tree::ptree::value_type;
using ByteBlockPair = std::pair<size_t, size_t>;

using BlockQueue = TSQueue<ValgrindBlock>;
using MaybeBlock = boost::optional<ValgrindBlock>;

// Valgrind <error> block definition
struct ValgrindFrame {
	std::string ip, obj, fn, dir, file, line;
	ValgrindFrame(PtreeVal const& fv, std::string const& targetExecutable) :
		ip  (fv.second.get<std::string>("ip", "")),
		obj (fv.second.get<std::string>("obj", "???")),
		fn  (fv.second.get<std::string>("fn", "???")),
		dir (fv.second.get<std::string>("dir", "")),
		file(fv.second.get<std::string>("file", targetExecutable)),
		line(fv.second.get<std::string>("line", "")) {}
};


template <typename T, typename U>
std::pair<T,U>& operator+=(std::pair<T,U>& l, const std::pair<T,U>& r) {
	l.first  += r.first;
	l.second += r.second;
	return l;
}

class ValgrindOutput {
	// preamble information
	size_t tidx;
	pid_t pid = 0, ppid = 0;
	std::string targetExecutable;

	// counts of errors, suppressions, contexts, bytes/blocks leaked
	std::unordered_map<std::string, size_t> counts;
	std::unordered_map<std::string, size_t> contexts;
	std::unordered_map<std::string, ByteBlockPair> leakInfo;
	std::string formattedMessage;

	// extract info from preamble, error, or leak ptree and update
	void readPreamble(const Ptree& pt);
	MaybeBlock readMessage(const Ptree& pt, int errorTag);

public:
	enum class Stage {
		Uninitialized, Preamble, Errors, Leaks
	} outputStage = Stage::Preamble;

	enum class Protocol {
		Undefined, Memcheck, Helgrind, Drd
	} protocol = Protocol::Undefined;

	const enum UseStacktraces {
		NoTraces,
		FullTraces
	} useStacktraces;

	ValgrindOutput(size_t tidx_, UseStacktraces useStacktraces_ = FullTraces) :
		tidx(tidx_), useStacktraces(useStacktraces_) {}

	// extract info from ptree, update internal data, add ValgrindBlock to workQueue
	MaybeBlock readPtree(const Ptree& pt) {
		switch (outputStage) {
			case Stage::Uninitialized: return boost::none;
			case Stage::Preamble:
			readPreamble(pt);
			break;
			case Stage::Errors:
			return readMessage(pt, APG_MSG);
			case Stage::Leaks:
			return readMessage(pt, APG_LEAK);
		}
		return boost::none;
	}

	std::string getSummary();
	size_t getTidx() const        { return tidx; }
	pid_t getPid() const          { return pid; }
	pid_t getPpid() const         { return ppid; }
	size_t getErrorCounts()       { return counts["errorcounts"]; }
	size_t getSuppCounts()        { return counts["suppcounts"]; }
	Stage getStage() const        { return outputStage; }

private:
	class ValgrindError {
		enum ErrorStage { Preamble, Stack, AuxStack } errorStage;
		std::string what, auxWhat;
		std::vector<ValgrindFrame> stack, auxStack;
		std::string formattedMessage;

	public:
		std::string kind;
		ByteBlockPair leaked;

		ValgrindError(
			ValgrindOutput::Protocol protocol,
			std::string const& targetExecutable,
			PtreeVal const& ov);
		std::string getString(UseStacktraces useStacktraces = FullTraces);
	};

	class ValgrindSignal {
		std::vector<ValgrindFrame> stack;
		std::string formattedMessage;

	public:
		std::string sigNo, sigName;

		ValgrindSignal(
			ValgrindOutput::Protocol protocol,
			std::string const& targetExecutable,
			PtreeVal const& ov);
		std::string getString();
	};
};

#endif
