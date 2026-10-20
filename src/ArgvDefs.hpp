/******************************************************************************\
 * ArgvDefs.hpp - Central argv definitions for strong_argv.hpp
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

#ifndef _ARGV_DEFS_H
#define _ARGV_DEFS_H

#include "utils/strong_argv.hpp"

using Option    = Argv::Option;
using Parameter = Argv::Parameter;

struct BackendArgv : public Argv {
	static constexpr Option BinaryUsesMPI { "uses-mpi", 'm' };
	static constexpr Option NoTimeout     { "no-timeout", 't' };
	static constexpr Option NoStacktraces { "no-stacktraces", 's' };

	static constexpr Parameter ActiveRankSet { "active-rank-set", 'a' };
	static constexpr Parameter QueueKey      { "queue-key", 'k' };

	static constexpr GNUOption long_options[] = {
		BinaryUsesMPI, NoTimeout, NoStacktraces,
		ActiveRankSet, QueueKey,
	long_options_done };
};

// flaw in C++11 relating to static constexpr. can be removed in C++17
using BA = BackendArgv;
constexpr Option    BA::BinaryUsesMPI, BA::NoTimeout, BA::NoStacktraces;
constexpr Parameter BA::ActiveRankSet, BA::QueueKey;
constexpr Argv::GNUOption BA::long_options[];

struct StarterArgv : Argv {
	static constexpr Option PalsBarrier { "pals-barrier", 'p' };

	static constexpr Parameter Binary       { "binary", 'e' };
	static constexpr Parameter BinaryArg    { "binary-arg", 'a' };
	static constexpr Parameter ValgrindTool { "valgrind-tool", 't' };
	static constexpr Parameter ValgrindArg  { "valgrind-arg", 'v' };
	static constexpr Parameter Suppressions { "suppressions", 's' };
	static constexpr Parameter QueueKey     { "queue-key", 'k' };

	static constexpr GNUOption long_options[] = {
		PalsBarrier,
		Binary, BinaryArg, ValgrindTool, ValgrindArg, Suppressions, QueueKey,
	long_options_done };
};

// flaw in C++11 relating to static constexpr. can be removed in C++17
using SA = StarterArgv;
constexpr Parameter SA::Binary, SA::BinaryArg, SA::ValgrindTool,
	SA::ValgrindArg, SA::Suppressions, SA::QueueKey;
constexpr Argv::GNUOption SA::long_options[];

struct ValgrindArgv : Argv {
	static constexpr Option TraceChildren          { "trace-children=yes", 1 };
	static constexpr Option XMLMode                { "xml=yes", 2 };
	static constexpr Option SilenceChildAfterFork  { "child-silent-after-fork=yes", 3 };
	// careful using this; it is known to break results on CS systems (PE-39119)
	static constexpr Option SonameTcmallocSynonyms {
		"soname-synonyms=somalloc=*tcmalloc*", 4
	};

	static constexpr Parameter Tool         { "tool", 10 };
	static constexpr Parameter XMLSocket    { "xml-socket", 11 };
	static constexpr Parameter Suppressions { "suppressions", 12 };

	static constexpr GNUOption long_options[] = {
		TraceChildren, XMLMode, SilenceChildAfterFork, SonameTcmallocSynonyms,
		Tool, XMLSocket, Suppressions,
	long_options_done };
};

// flaw in C++11 relating to static constexpr. can be removed in C++17
using VA = ValgrindArgv;
constexpr Option    VA::TraceChildren, VA::XMLMode,
	VA::SilenceChildAfterFork, VA::SonameTcmallocSynonyms;
constexpr Parameter VA::Tool, VA::XMLSocket, VA::Suppressions;
constexpr Argv::GNUOption VA::long_options[];

#endif
