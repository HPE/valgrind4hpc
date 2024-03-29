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

struct FrontendArgv : public Argv {
	static constexpr Option NoTimeout { "no-timeout", '\1' };
	static constexpr Option NoStacktrace { "no-stacktrace", '\2' };
	static constexpr Option Help { "help", 'h' };

	static constexpr Parameter NumRanks { "num-ranks", 'n' };
	static constexpr Parameter Tool { "tool", 't' };
	static constexpr Parameter LauncherArgs { "launcher-args", 'l' };
	static constexpr Parameter Inputfile { "inputfile", 'i' };
	static constexpr Parameter Outputfile { "outputfile", 'o' };
	static constexpr Parameter Suppressions { "suppressions", 's' };
	static constexpr Parameter ValgrindArgs { "valgrind-args", 'v' };
	static constexpr Parameter FromRanks { "from-ranks", 'r' };
	static constexpr Parameter VgdbError { "vgdb-error", 'g' };
	static constexpr Parameter CrayPmi { "cray-pmi", '\3' };
	static constexpr Parameter WithCce { "with-cce", '\4' };
	static constexpr Parameter GenSuppressions { "gen-suppressions", '\5' };
	static constexpr Parameter GenSuppressionsFile { "gen-suppressions-fil", '\6' };

	static constexpr GNUOption long_options[] = {
		NoTimeout, NoStacktrace, Help,
		NumRanks, Tool, LauncherArgs, Inputfile, Outputfile, Suppressions,
		ValgrindArgs, FromRanks, VgdbError, CrayPmi, WithCce, GenSuppressions,
		GenSuppressionsFile,
	long_options_done };
};

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

#endif
