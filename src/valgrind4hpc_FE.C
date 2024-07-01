/******************************************************************************\
 * valgrind4hpc_FE.C - Front end client of parallel valgrind tool.
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

// strings & IO
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>

// threading
#include <thread>
#include <atomic>
#include <mutex>
#include <condition_variable>
#include <chrono>

// containers
#include <map>
#include <unordered_map>
#include <vector>

// directory traversal
#include <dirent.h>
#include <libgen.h>

// fork / exec
#include <sys/types.h>
#include <sys/wait.h>

// signal handling
#include <signal.h>

// gnu extensions
#include <getopt.h>

// MRNet / CTI
#include "mrnet/MRNet.h"
#include "common_tools_fe.h"

// valgrind4hpc definitions
#include "valgrind4hpc_protocol.h"
#include "valgrind4hpc_defs.h"
#include "ArgvDefs.hpp"

// aggregator implementations
#include "valgrind4hpc_aggregator.h"

#include "utils/ExecvpOutput.hpp"
#include "utils/make_unique.hpp"

#include "TopoNode.hpp"

//std::ostream dbg_stream(std::cout.rdbuf());
NullStream dbg_stream;

// prototypes
static std::unique_ptr<MRN::Network>
BuildNetwork(cti_app_id_t appId, cti_manifest_id_t mid, rank_set_t const& activeRankSet);

// global variables

static const size_t NUM_STREAMS = 5;  // cmd, msg, leak, count, summary_stream

static int quiet_mode = false;
static int no_stacktrace_mode = false;
static int no_timeout_mode = false;
static bool mpi_binary = true;

static cti_app_id_t appId = 0;
static size_t num_mrnet_nodes = 0;
static size_t num_daemons = 0;
static size_t num_ranks = 0;

static bool finish = false;
static std::mutex finish_mtx;
static std::condition_variable finish_cv;

static std::mutex mtx;

static int unique_errors = 0;

using AggregatorPtr = std::unique_ptr<Aggregator<std::string>>;
static AggregatorPtr masterErrorAgg, masterLeakAgg, masterSummaryAgg, masterSuppressionAgg;

static std::atomic<size_t> streams_exited(0);
static std::atomic<size_t> total_errors(0);
static std::atomic<size_t> total_suppressions(0);

static std::streambuf *output_buf;
static std::ofstream output_file;

static int key;

std::string get_bin_path(const char *binname)
{
	const char* const argv[3] = {"which", binname, nullptr};
	ExecvpOutput whichOutput("which", (char* const*)argv);

	if (whichOutput.getExitStatus() != 0) {
		return "";
	}

	if (const auto& path = whichOutput.optional_getline()) {
		return path.get();
	}

	return "";
}

static const std::vector<const char*> parallel_init_symbols = {"PMI2_Init", "MPI_Init", "__pgas_check_s", "shmem_init", "start_pes"};
bool is_parallel_binary(const char *binpath)
{

	const char* const argv[4] = {"objdump", "-t", binpath, nullptr};
	ExecvpOutput objdumpOutput("objdump", (char* const*)argv);

	bool header_found = false;
	bool pmi_symbol_found = false;
	bool no_symbols_found = false;
	while (boost::optional<std::string> line = objdumpOutput.optional_getline()) {
		size_t found;
		// Only check for header information if we haven't seen it yet
		if (!header_found) {
			found = line->find("SYMBOL TABLE:");
			if ( found != std::string::npos ) {
				header_found = true;
				// The next line will contain "no symbols" if symbol information was stripped
				found = objdumpOutput.optional_getline()->find("no symbols");
				if (found != std::string::npos) {
					no_symbols_found = true;
					break;
				}
			}
			// Ignore this line, it a line before the symbol information
			continue;
		}
		// Header found, this line has symbol information in it
		for (auto& sym : parallel_init_symbols) {
			found = line->find(sym);
			if ( found != std::string::npos ) {
				pmi_symbol_found = true;
				break;
			}
		}
		if (pmi_symbol_found) break;
	}

	// If we never found the header, something is very wrong.
	if ( !header_found )	no_symbols_found = true;
	
	int objdumpStatus = objdumpOutput.getExitStatus();
	if (objdumpStatus > 0) {
		throw std::runtime_error("objdump failed with return code " + std::to_string(objdumpStatus));;
	}

	if (no_symbols_found) {
		fprintf(stderr, "Valgrind4hpc uses debug symbols to automatically check for Cray-specific functions.\n");
		fprintf(stderr, "Please compile with debug symbols or specify the argument --cray-pmi={yes|no}\n");
		fprintf(stderr, "Pass --cray-pmi=yes if debugging a parallel app, --cray-pmi=no otherwise\n");
		exit(1);
	}

	return pmi_symbol_found;
}

bool is_dynamic_binary(const char *binpath)
{
	const char* const argv[3] = {"ldd", binpath, nullptr};
	return 0 == ExecvpOutput("ldd", (char* const*)argv).getExitStatus();
}

void print_msg(std::pair<std::string, rank_set_t> evicted, std::ostream &output_stream){
	output_stream << std::endl;
	readable_ranks(output_stream, evicted.second);
	output_stream << evicted.first << std::endl; 
}

// MRNet callbacks
void
mrnet_data_callback(MRN::Event* e, void * cb_data)
{
	dbg_stream << "callback started" << std::endl;
	cb_data = NULL;

	MRN::DataEvent::DataEventData* data = (MRN::DataEvent::DataEventData*)e->get_Data();
	MRN::Stream* stream = data->get_Stream();
	MRN::PacketPtr buf;
	
	std::ostream output_stream(output_buf);
	
	int	tag = 0;
	
	if (stream->recv(&tag, buf) == -1)
	{
		throw std::runtime_error("MRNet Stream::recv failed.");
	}
	dbg_stream << "got message with tag " << tag << std::endl;

	if (tag == APG_STREAMS_OK)
	{
		return;
	} else if ((tag == APG_MSG) || (tag == APG_LEAK) || (tag == APG_SUMMARY)
		    || (tag == APG_SUPPRESSION))
	{
		AggregatorPtr& target =
			(tag == APG_MSG)  ? masterErrorAgg :
			(tag == APG_LEAK) ? masterLeakAgg :
			(tag == APG_SUMMARY) ? masterSummaryAgg :
			masterSuppressionAgg;

		char ** msg = NULL;
		size_t msgLen = 0;
		buf->unpack(APG_AGGREGATE_FS, &msg, &msgLen);

		//grab global mutex
		{ std::lock_guard<std::mutex> lck(mtx);
			for (size_t i = 0; i < msgLen; ++i)
			{
				if (tag == APG_MSG) {
					unique_errors++;
				}

				std::string msg_str;
				rank_set_t *rank_ptr;
				parse_msg(msg[i], &msg_str, &rank_ptr);

				if (boost::optional<std::pair<std::string, rank_set_t>> evicted = target->merge(msg_str, *rank_ptr)) {
					print_msg(evicted.get(), output_stream);
				}

				free(msg[i]);
			}
		}
		
		free(msg);
	} else if ((tag == APG_ERROR_COUNT) || (tag == APG_SUPPRESSION_COUNT))
	{
		std::atomic<size_t> *target = NULL;
		if (tag == APG_ERROR_COUNT) { target = &total_errors; }
		else { target = &total_suppressions; }
		
		char ** msg = NULL;
		size_t msgLen = 0;
		
		buf->unpack(APG_AGGREGATE_FS, &msg, &msgLen);
		
		for (size_t i = 0; i < msgLen; ++i)
		{
			dbg_stream << "count msg " << i << ": " << msg[i] << std::endl;
			std::string tmp(msg[i]);
			tmp.erase(0, tmp.find('\n')+1);
			*target += stoi(tmp);
			free(msg[i]);
		}
		
		free(msg);
	} else if (tag == APG_EXIT)
	{
		if(strcmp(buf->get_FormatString(), "%ud") == 0)
		{
			size_t exit_val = 0;
			buf->unpack("%ud", &exit_val);
			streams_exited += exit_val;
		}else
		{
			char** exit_string;
			size_t exit_len = 0;
			
			buf->unpack("%as", &exit_string, &exit_len);
				
			for(unsigned int i = 0; i < exit_len; ++i)
			{
				streams_exited += atoi(exit_string[i]);
			}
		}

		if (streams_exited == (NUM_STREAMS * num_mrnet_nodes))
		{
			std::unique_lock<std::mutex> lck(finish_mtx);
			finish = true;
			lck.unlock();
			finish_cv.notify_all();
		}
	}
	else { throw std::runtime_error("Recieved unexpected MRNet tag!"); }
}

#include <iomanip>
static void
usage(char* const* argv, int code) {
	auto& out = (code > 0) ? stderr : stdout;

	fprintf(out, "Usage: %s [VALGRIND4HPC OPTIONS]... executable -- [EXECUTABLE OPTIONS]...\n", argv[0]);
	fprintf(out, "Check for memory leaks and errors and aggregate results from multiple ranks.\n\n");

	using FA = FrontendArgv;
	fprintf(out, "  -%c, --%s  Run with <n> ranks [default: 1]\n",
		FA::NumRanks.val, FA::NumRanks.name);
	fprintf(out, "  -%c, --%s  Run with specified valgrind tool: memcheck, helgrind, exp-sgcheck, drd. [default: memcheck]\n",
		FA::Tool.val, FA::Tool.name);
	fprintf(out, "  -%c, --%s  Pass launcher specific arguments <args> to the application launcher, e.g. -l\"-N1.\"\n",
		FA::LauncherArgs.val, FA::LauncherArgs.name);
	fprintf(out, "  -%c, --%s  Provide input to all ranks from <file>.\n",
		FA::Inputfile.val, FA::Inputfile.name);
	fprintf(out, "  -%c, --%s  Log output messages to <file>.\n",
		FA::Outputfile.val, FA::Outputfile.name);
	fprintf(out, "  -%c, --%s  Suppress valgrind errors described in <file>. Can be used multiple times for each suppression file.\n",
		FA::Suppressions.val, FA::Suppressions.name);
	fprintf(out, "       --%s  Generate suppressions for this job [yes|no]\n",
		FA::GenSuppressions.name);
	fprintf(out, "       --%s  Write generated suppressions to this file\n",
		FA::GenSuppressionsFile.name);
	fprintf(out, "  -%c, --%s  Pass tool specific arguments <args> to valgrind.\n",
		FA::ValgrindArgs.val, FA::ValgrindArgs.name);
	fprintf(out, "  -%c, --%s  Only debug / show output from certain ranks, e.g. -r\"0-2,4\" to exclude rank 3\n",
		FA::FromRanks.val, FA::FromRanks.name);
	fprintf(out, "  -%c, --%s  Start VGDB mode upon encountering this number of errors\n",
		FA::VgdbError.val, FA::VgdbError.name);
	fprintf(out, "  -%c, --%s  Display this text and exit\n",
		FA::Help.val, FA::Help.name);

	fprintf(out, "\nExample:\n"
		"  %s -n32 --launcher-args=\"-N16 -j2\" --valgrind-args=\"--track-origins=yes "
		"--leak-check=full\" ./a.out -- arg1 arg2\n"
		"Note that %s arguments and target executable arguments are seperated by '--'\n",
		argv[0], argv[0]);

	exit(code);
}

static void
bad_optarg(char* const* argv, const char *argname, const char *said)
{
	if (said == NULL) {
		fprintf(stderr, "%s: argument required for %s (none given)\n", argv[0], argname);
	} else {
		fprintf(stderr, "%s: bad option for %s (provided %s)\n", argv[0], argname, said);
	}
	fprintf(stderr, "%s: Use --help for more information or consult the user manual.\n", argv[0]);
	exit(1);
}

static void
early_shutdown() {
	signal(SIGINT, SIG_IGN);

	// tell CTI to send SIGINT
	if (appId != 0) {
		cti_killApp(appId, SIGINT);
	}

	// inform main loop to read out remaining errors and shut down
	std::unique_lock<std::mutex> lck(finish_mtx);
	finish = true;
	lck.unlock();
	finish_cv.notify_all();

	// restore default SIGINT behavior
	signal(SIGINT, SIG_DFL);
}

static void
handle_sigint(int sig)
{
	if (sig != SIGINT) {
		return;
	}
	std::thread{early_shutdown}.detach();
}

struct ParsedArgs
{
	std::string valgrind_tool;
	std::string launcher_args;
	std::string extra_valgrind_args;
	std::string input_file_path;
	std::string output_file_path;
	std::string rank;
	std::string from_ranks;
	std::string with_mpi;
	std::string with_cce;
	std::string vgdb_error;
	std::string gen_suppressions;
	std::string gen_suppressions_file;
	std::vector<std::string> suppression_files;
	bool no_timeout_mode;
	bool no_stacktrace_mode;
	int rest_argc;
	char** rest_argv;
};

static auto parse_argv(int argc, char** argv)
{
	auto result = ParsedArgs{};

	using FA = FrontendArgv;
	auto parsedArgv = IncomingArgv<FrontendArgv>{argc, argv};
	while (true) {
		auto&& [c, value] = parsedArgv.get_next();
		if (c <= 0) { break; }

		switch (c) {

		case FA::NumRanks.val:
			result.rank = std::move(value);
			break;

		case FA::Tool.val:
			if ((value == "memcheck") || (value == "helgrind")
			 || (value == "drd") || (value == "exp-sgcheck")) {
				result.valgrind_tool = value;
			} else {
				bad_optarg(argv, FA::Tool.name, value.c_str());
			}
			break;

		case FA::LauncherArgs.val:
			result.launcher_args = std::move(value);
			break;

		case FA::Inputfile.val:
			result.input_file_path = std::move(value);
			break;

		case FA::Outputfile.val:
			result.output_file_path = std::move(value);
			break;

		case FA::Suppressions.val:
			result.suppression_files.push_back(std::move(value));
			break;

		case FA::ValgrindArgs.val:
			result.extra_valgrind_args = std::move(value);
			break;

		case FA::FromRanks.val:
			result.from_ranks = std::move(value);
			break;

		case FA::VgdbError.val:
			result.vgdb_error = std::move(value);

		case FA::NoTimeout.val:
			result.no_timeout_mode = true;
			break;

		case FA::NoStacktrace.val:
			result.no_stacktrace_mode = true;
			break;

		case FA::CrayPmi.val:
			if ((value == "yes") || (value == "no")) {
				result.with_mpi = std::move(value);
			} else {
				bad_optarg(argv, FA::CrayPmi.name, value.c_str());
			}
			break;

		case FA::WithCce.val:
			if ((value == "yes") || (value == "no")) {
				result.with_cce = std::move(value);
			} else {
				bad_optarg(argv, FA::WithCce.name, value.c_str());
			}
			break;

		case FA::GenSuppressions.val:
			if ((value == "yes") || (value == "no") || (value == "all")) {
				result.gen_suppressions = std::move(value);
			} else {
				bad_optarg(argv, FA::GenSuppressions.name, optarg);
			}
			break;

		case FA::GenSuppressionsFile.val:
			result.gen_suppressions_file = std::move(value);
			break;

		case FA::Help.val:
			usage(argv, 0);
		default:
			usage(argv, 1);
		}
	}

	std::tie(result.rest_argc, result.rest_argv) = parsedArgv.get_rest();

	// set variables based on optargs
	if (result.rest_argv[0] == NULL)
	{
		fprintf(stderr, "%s: target executable argument required (none given)\n", argv[0]);
		usage(argv, 1);
	}

	return result;
}

int
main(int argc, char** argv)
{	
	int ret = 0;
	output_buf = std::cout.rdbuf();

	// Parse arguments
	auto args = parse_argv(argc, argv);
	auto executable = std::string{args.rest_argv[0]};

	// Open output file
	if (!args.output_file_path.empty()) {
		output_file.open(std::string(optarg));
		output_buf = output_file.rdbuf();
	}

	try
	{
		cti_session_id_t sid = 0;
		cti_manifest_id_t mid = 0;
		MRN::Communicator* comm = NULL;
		int aggregate_filter_id;
		int leak_filter_id;
		int summary_filter_id;
		int pair_sum_filter_id;
		int sum_filter_id;

		std::string valgrind_bin_path;
		std::string install_lib_valgrind;

		// get/set environment variables
		char *benv;
		if ((benv = getenv(APG_BASE_DIR_ENV)) == NULL) {
			throw std::runtime_error("VALGRIND4HPC_INSTALL_DIR env variable not set!");
		}
		std::string basePath(benv);

		// check if valgrind exists and set cores base path
		if (const char* vld = getenv(APG_VALGRIND_DIR_ENV)) {
			std::string user_valgrind_install_path = std::string(vld);
			printf("Using Valgrind: %s\n",user_valgrind_install_path.c_str());
			valgrind_bin_path = user_valgrind_install_path + "/bin";
			install_lib_valgrind = user_valgrind_install_path + "/lib/valgrind";
		}
		else{
			// check for valgrind binary included with install
			std::string tmp = basePath + "/bin/valgrind";
			struct stat st;
			if (stat(tmp.c_str(), &st) == 0) {
				// use packaged valgrind
				valgrind_bin_path = tmp;
				// Do not inform user of this
			}
			else {
				valgrind_bin_path = get_bin_path("valgrind");
				if (valgrind_bin_path.empty()) {
					printf("Can't find valgrind in PATH. Check with `which valgrind`.");
					exit(1);
				}
				std::cout << "Using Valgrind: " << valgrind_bin_path << std::endl;
			}
		}

		std::string valgrind_lib_base;
		{ CStrPtr vlb(strdup(valgrind_bin_path.c_str()), free);
			valgrind_lib_base = std::string(dirname(vlb.get())); // FIXME: this can be changed when building valgrind from source
		}

		struct stat st;
		if (stat((valgrind_lib_base + "/../libexec/valgrind/").c_str(), &st) == 0) {
			valgrind_lib_base += "/../libexec/valgrind/";
		} else { // if it's not actually here, it will error during the library check and print a message
			valgrind_lib_base += "/../lib/valgrind/";
		}
		if (!install_lib_valgrind.empty()) {
			// reenable for non-internal release fprintf(stderr, "VALGRIND_LIB set; using custom directory for core files: %s\n", install_lib_valgrind);
			valgrind_lib_base = install_lib_valgrind + "/";
		}

		/* set architecture-specific valgrind filenames */
		#if defined(__x86_64__)
			#define ARCH "amd64"
		#elif defined(__aarch64__)
			#define ARCH "arm64"
		#else
			#error "unsupported architecture"
		#endif
		const std::string memcheck_libs[] = {"memcheck-" ARCH "-linux",
		                                     "vgpreload_memcheck-" ARCH "-linux.so",
		                                     "vgpreload_core-" ARCH "-linux.so",
		                                     "default.supp"};
		const std::string helgrind_libs[] = {"helgrind-" ARCH "-linux",
		                                     "vgpreload_helgrind-" ARCH "-linux.so",
		                                     "vgpreload_core-" ARCH "-linux.so",
		                                     "default.supp"};
		const std::string drd_libs[] = {"drd-" ARCH "-linux",
		                                "vgpreload_drd-" ARCH "-linux.so",
		                                "vgpreload_core-" ARCH "-linux.so",
		                                "default.supp"};
		const std::string sgcheck_libs[] = {"exp-sgcheck-" ARCH "-linux",
		                                    "vgpreload_exp-sgcheck-" ARCH "-linux.so",
		                                    "vgpreload_core-" ARCH "-linux.so",
		                                    "default.supp"};
		#undef ARCH
		for (auto lib : memcheck_libs) {
			if (access((valgrind_lib_base + lib).c_str(), R_OK) != 0) {
				throw std::runtime_error("can't find valgrind core: " + lib + ". Check with `valgrind -d | grep " + lib + "`, optionally set VALGRIND_LIB path");
			}
		}

		// keep this for a potential mainline valgrind release that includes the hugepages fix
		/*
		FILE *vv_file = popen("valgrind --version", "r");
		if (vv_file == NULL) throw std::runtime_error("error checking `valgrind --version`");
		int vv_major, vv_minor;
		int vv_result = fscanf(vv_file, "valgrind-%d.%d.*", &vv_major, &vv_minor);
		if (vv_result < 2) throw std::runtime_error("error parsing `valgrind --version`");
		fclose(vv_file);
		if ((vv_major < 3) || ((vv_major == 3) && (vv_minor < 10)))
		{
			dbg_stream << "WARNING: your valgrind version (" << vv_major << "." << vv_minor << ".*) does not fully support hugepage (minimum 3.10). You may experience MPI \"out of memory errors\" when running with many ranks. Valgrind bug 333051" << std::endl;
		}
		*/
		
		// Adjust PATH to prepend MRNet and Valgrind4hpc paths
		auto newPath = std::string{};
		// XXX: The newPath MUST COME FIRST!!! Totalview isn't doing things
		//      properly and is exposing an mrnet_commnode that is incompatible
		//      with us.
		if (auto path = ::getenv("PATH")) {
			newPath = std::string{path};
		}

		// Prepend MRNet libexec directory for commnode
		if (auto mrnet_install_dir = ::getenv("MRNET_INSTALL_DIR")) {
			auto mrnetLibexecDir = std::string{mrnet_install_dir} + "/libexec";
			newPath = mrnetLibexecDir + ":" + newPath;

		// Print warning
		} else {
			fprintf(stderr, "MRNet install location was not found in "
				"environment. Tool launch may fail. Load the `cray-mrnet` "
				"module, or set MRNET_INSTALL_DIR to the system MRNet "
				"installation path\n");
		}

		// Prepend Valgrind4hpc libexec directory for starter
		newPath = basePath + "/libexec:" + newPath;

		// Set PATH
		if(setenv("PATH", newPath.c_str(), 1) != 0)
			throw std::runtime_error("Failed to setenv PATH");
		
		if(setenv("PMI_NO_FORK", "1", 1)!=0)
			throw std::runtime_error("Failed to setenv PMI_NO_FORK");

		if(setenv("LIBALPS_ENABLE_DSL", "1", 1)!=0)
			throw std::runtime_error("Failed to setenv LIBALPS_ENABLE_DSL");

		// set CTI timeout attributes
		if (cti_setAttribute(CTI_PMI_FOPEN_TIMEOUT, "3000")) {
			throw std::runtime_error("Failed to set CTI_PMI_FOPEN_TIMEOUT: " + std::string{cti_error_str()});
		}
		if (cti_setAttribute(CTI_EXTRA_SLEEP, "15")) {
			throw std::runtime_error("Failed to set CTI_EXTRA_SLEEP: " + std::string{cti_error_str()});
		}

		// Add every default suppression file in the basePath/share/suppressions directory.
		// Note that this path *MUST* match the $suppdir defined in the suppressions Makefile.am...
		std::string suppPath = basePath + "/share/suppressions/";

		// Check the environment override variable to disable default supressions
		char *senv = getenv(APG_IGNORE_SUPP_ENV);
		// ONLY proceeed if it is not set!
		if (senv == NULL) {
			DIR* dirp = opendir( suppPath.c_str() );
			struct dirent* dp;
			while ((dp = readdir(dirp)) != NULL) {
				// Ignore files that start with '.'
				if (dp->d_name[0] == '.')	continue;
				args.suppression_files.push_back(suppPath + dp->d_name);
			}
			closedir(dirp);
		}

		// Check provided executable
		if (executable.empty())
		{
			fprintf(stderr, "%s: target executable argument required (none given)\n", argv[0]);
			usage(argv, 1);
		}

		std::string executable_path = get_bin_path(executable.c_str());
		if (executable_path.empty())
		{
			fprintf(stderr, "%s: could not find target executable %s\n", argv[0], executable.c_str());
			exit(1);
		}

		if (!strcmp(cti_wlm_type_toString(cti_current_wlm()), "Cray ALPS"))
		{ // FIXME: workaround a CTI issue where pmi_attribs is never created for non-MPI programs
			if (args.with_mpi.empty()) // but only on ALPS (SLURM / CS use proctable)
			{
				mpi_binary = is_parallel_binary(executable_path.c_str());
				if (!mpi_binary && !quiet_mode) {
					fprintf(stderr, "Valgrind4hpc did not detect a Cray parallel model in your application.\n");
					fprintf(stderr, "If your application uses a parallel model, rank information may be inaccurate.\n");
					fprintf(stderr, "To override: pass the argument --cray-pmi=yes. Press <enter> to continue debugging.\n");
					getchar();
				}
			} else
			{
				mpi_binary = (args.with_mpi.compare("yes") == 0) ? true : false;
			}
		} else {
			mpi_binary = true;
		}

		if (args.with_cce.empty())
		{
			bool dynamic_binary = is_dynamic_binary(executable_path.c_str());
			if (!dynamic_binary && !quiet_mode) {
				fprintf(stderr, "Valgrind4hpc detected that your application was compiled statically.\n");
				fprintf(stderr, "If your application was compiled using CCE, memory leak information will be inaccurate.\n");
				fprintf(stderr, "If using CCE, set the environment variable CRAYPE_LINK_TYPE=dynamic when compiling.\n");
				fprintf(stderr, "To override: pass the argument --with-cce=no. Press <enter> to continue debugging.\n");
				getchar();
			}
		} else if (!args.with_cce.compare("yes"))
		{
			bool dynamic_binary = is_dynamic_binary(executable_path.c_str());
			if (!dynamic_binary) {
				fprintf(stderr, "Valgrind4hpc detected that your application was compiled statically.\n");
				fprintf(stderr, "You specified --with-cce=yes; memory leak information will be inaccurate.\n");
				fprintf(stderr, "Set the environment variable CRAYPE_LINK_TYPE=dynamic when compiling your program.\n");
				exit(1);
			}
		}

		// Parse number of ranks
		num_ranks = 1;
		if (!args.rank.empty()) {
			try {
				num_ranks = std::stoi(args.rank);
			} catch (...) {
				throw std::invalid_argument(std::string("number of ranks as '") + args.rank + "'");
			}
		}

		// Create active rank set
		rank_set_t activeRankSet(num_ranks);
		if (args.from_ranks.empty()) {
			activeRankSet.set();

		} else {
			std::stringstream ss(args.from_ranks);
			std::string rank;
			while (std::getline(ss, rank, ',')) {
				size_t from, to;

				// parse rank range
				{ std::string fromStr, toStr;
					{ std::stringstream ss(rank);
						if (std::getline(ss, fromStr, '-')) {
							std::getline(ss, toStr);
						}
					}
					if (toStr.empty()) {
						toStr = fromStr;
					}

					try {
						from = std::stoi(fromStr);
						to   = std::stoi(toStr);
					} catch(...) {
						bad_optarg(argv, "-r, --from-ranks", rank.c_str());
					}
				}

				// validate rank range
				if ((from > to) || (from >= num_ranks) || (to >= num_ranks)) {
					bad_optarg(argv, "-r, --from-ranks rank number", rank.c_str());
				}

				for (size_t i = from; i <= to; i++) {
					activeRankSet.set(i);
				}
			}
		}

		// Create the aggregators
		masterLeakAgg = shim::make_unique<FullTimerAggregator<std::string>>(10, activeRankSet);
		masterErrorAgg = shim::make_unique<FullTimerAggregator<std::string>>(10, activeRankSet);
		masterSummaryAgg = shim::make_unique<NoEvictAggregator<std::string>>(activeRankSet);
		masterSuppressionAgg = shim::make_unique<NoEvictAggregator<std::string>>(activeRankSet);

		// launcher_argv part 1: aprun arguments
		ManagedArgv launcher_argv;

		launcher_argv.add("-n" + std::to_string(num_ranks));
		if (!args.launcher_args.empty()) {
			std::istringstream buf(args.launcher_args);
			std::istream_iterator<std::string> beg(buf), end;
			for (auto it : std::vector<std::string>(beg, end)) {
				launcher_argv.add(it);
			}
		}

		// starter argv: target executable and arguments
		OutgoingArgv<StarterArgv> starterArgv(APG_STARTER);

		if (cti_current_wlm() == CTI_WLM_PALS) {
			starterArgv.add(StarterArgv::PalsBarrier);
		}
		starterArgv.add(StarterArgv::Binary, args.rest_argv[0]);
		for (int i = 1; i < args.rest_argc; i++) {
			starterArgv.add(StarterArgv::BinaryArg, args.rest_argv[i]);
		}

		// starter argv: optional valgrind arguments
		if (args.valgrind_tool.empty()) { args.valgrind_tool = std::string("memcheck"); }
		starterArgv.add(StarterArgv::ValgrindTool, args.valgrind_tool);
		for (const auto& supp_path : args.suppression_files) {
			CStrPtr basenameTarget(strdup(supp_path.c_str()), free);
			starterArgv.add(StarterArgv::Suppressions, basename(basenameTarget.get()));
		}
		if (!args.extra_valgrind_args.empty()) {
			std::istringstream ss(args.extra_valgrind_args);
			std::string arg;
			while (std::getline(ss, arg, ' ')) {
				starterArgv.add(StarterArgv::ValgrindArg, arg);
			}
		}
		if (!args.vgdb_error.empty()) {
			starterArgv.add(StarterArgv::ValgrindArg, "--vgdb-error=" + args.vgdb_error);
		}
		if (args.gen_suppressions.empty() && !args.gen_suppressions_file.empty()) {
			// Default to enabled if generated suppressions file set
			args.gen_suppressions = "yes";
		}
		// "yes" is interactive in Valgrind, set to "all"
		if (args.gen_suppressions == "yes") {
			args.gen_suppressions = "all";
		}
		if (!args.gen_suppressions.empty()) {
			starterArgv.add(StarterArgv::ValgrindArg, "--gen-suppressions=" + args.gen_suppressions);
		}

		// launcher_argv part 5: random seed

		// We need to generate a good seed to avoid collisions. Since this
		// library can be used by automated tests, it is vital to have a
		// good seed.
		
		struct timespec     tv;
		unsigned int        pval;
		unsigned int        seed;

		// get the current time from epoch with nanoseconds
		
		if (clock_gettime(CLOCK_REALTIME, &tv))
		{
			throw std::runtime_error("Failed to get time!");
		}
		
		// generate an appropriate value from the pid, we shift this to
		// the upper 16 bits of the int. This should avoid problems with
		// collisions due to slight variations in nano time and adding in
		// pid offsets.
		
		pval = (unsigned int)getpid() << ((sizeof(unsigned int) * CHAR_BIT) - 16);

		// Generate the seed. This is not crypto safe, but should have enough
		// entropy to avoid the case where two procs are started at the same
		// time that use this interface.
		
		seed = (tv.tv_sec ^ tv.tv_nsec) + pval;
		srand(seed);
		
		// generate key for msg queue
		key = rand();
		starterArgv.add(StarterArgv::QueueKey, std::to_string(key));

		// Copy generated starter args to launcher args
		for (char* const* arg = starterArgv.get(); *arg != NULL; arg++) {
			launcher_argv.add(*arg);
		}

		dbg_stream << "reached CTI setup. launchApp(";
		for (auto arg = launcher_argv.get(); *arg != nullptr; arg++) {
			dbg_stream << *arg << ", ";
		}
		dbg_stream << ")" << std::endl;

		// set up cti
		std::string filterPath    = basePath + "/lib/libvalgrind4hpc_filters.so";
		std::string dmappWrapPath = basePath + "/lib/dmapp-wrap.so";

		// register signal handler for SIGINT
		{ struct sigaction action{};
			action.sa_handler = handle_sigint;
			sigaction(SIGINT, &action, nullptr);
		}

		try {
			appId = cti_launchApp(launcher_argv.get(), -1, -1,
				args.input_file_path.empty() ? nullptr : args.input_file_path.c_str(),
				nullptr, nullptr); // launch the valgrindized app
			if (appId == 0) { throw std::runtime_error("cti_launchApp"); }
		
			sid = cti_createSession(appId); // create a session
			if (sid == 0) { throw std::runtime_error("cti_createSession"); }
			
			mid = cti_createManifest(sid); // create a manifest
			if (mid == 0) { throw std::runtime_error("cti_createManifest"); }
			
			if (cti_addManifestBinary(mid, "valgrind")) { throw std::runtime_error("valgrind binary"); } // add valgrind binary
			if (!args.valgrind_tool.compare("helgrind")) {
				for (auto& lib : helgrind_libs) {
					if (cti_addManifestLibrary(mid, (valgrind_lib_base + lib).c_str())) { throw std::runtime_error(lib); }
				}
			} else if (!args.valgrind_tool.compare("drd")) {
				for (auto& lib : drd_libs) {
					if (cti_addManifestLibrary(mid, (valgrind_lib_base + lib).c_str())) { throw std::runtime_error(lib); }
				}
			} else if (!args.valgrind_tool.compare("exp-sgcheck")) {
				for (auto& lib : sgcheck_libs) {
					if (cti_addManifestLibrary(mid, (valgrind_lib_base + lib).c_str())) { throw std::runtime_error(lib); }
				}
			} else {
				// add default memcheck wrappers
				for (auto& lib : memcheck_libs) {
					if (cti_addManifestLibrary(mid, (valgrind_lib_base + lib).c_str())) { throw std::runtime_error(lib); }
				}

				// add dmapp-specific wrapper if present
				if (cti_addManifestLibrary(mid, dmappWrapPath.c_str())) {
					dbg_stream << "dmapp wrapper " << dmappWrapPath << " not found" << std::endl;
				}
			}

			// Add VGDB binary if VGDB mode enabled
			if (!args.vgdb_error.empty()) {
				if (cti_addManifestBinary(mid, "vgdb")) {
					throw std::runtime_error("failed to find vgdb binary");
				}
			}

			if (cti_addManifestBinary(mid, "valgrind4hpc_daemon")) { throw std::runtime_error("valgrind4hpc_daemon"); }
			
			if (cti_addManifestLibrary(mid, filterPath.c_str())) { throw std::runtime_error("MRNet filters"); }

			//Custom and default suppression
			for (auto& it : args.suppression_files)
			{
				if (cti_addManifestFile(mid, it.c_str())) { throw std::runtime_error(it); }
			}
			
		} catch (std::exception& e) {
			throw std::runtime_error(std::string("CTI Error (") + e.what() + "): " + cti_error_str());
		}

		cti_killApp(appId, SIGCONT); // FIXME: need to find main reason why the valgrind4hpc_starter PIDs "start" sigstopped on CS: cs-support

		dbg_stream << "building MRNet" << std::endl;
		
		// Build the MRNet network
		using NetPtr = std::unique_ptr<MRN::Network>;
		NetPtr net(std::move(BuildNetwork(appId, mid, activeRankSet)));
		if (net == nullptr) {
			throw std::runtime_error("Failed to build MRNet network (BuildNetwork returned nullptr).");
		} else if (net->has_Error()) {
			throw std::runtime_error(std::string("Failed to build MRNet network (") + net->get_ErrorStr(net->get_Error()) + ")");
		}
		
		// register the MRNet event callbacks
		net->register_EventCallback(MRN::Event::DATA_EVENT, MRN::DataEvent::DATA_AVAILABLE, mrnet_data_callback, NULL);
		//net->register_EventCallback(MRN::Event::ERROR_EVENT, MRN::Event::EVENT_TYPE_ALL, mrnet_error_callback, NULL);
	
		// load the filter functions into the network
		std::vector<const char *> filter_funcs = {"ApgrindAggregate",
		                                          "ApgrindLeaks",
		                                          "ApgrindSummaries",
		                                          "ApgrindPairSum",
		                                          "ApgrindSum"};
		std::vector<int> filter_ids;
		if (net->load_FilterFuncs(filterPath.c_str(), filter_funcs, filter_ids) != (int)filter_funcs.size())
		{
			throw std::runtime_error("MRNet load_FilterFuncs failed.");
		}
		aggregate_filter_id = filter_ids[0];
		leak_filter_id = filter_ids[1];
		summary_filter_id = filter_ids[2];
		pair_sum_filter_id = filter_ids[3];
		sum_filter_id = filter_ids[4];

		// get a broadcast stream for the back-ends
		comm = net->get_BroadcastCommunicator();
		if (comm == NULL)
		{
			throw std::runtime_error("MRNet get_BroadcastCommunicator() failed.");
		}

		// set up and configure MRNet command / message streams
		struct MRNStream {
			MRN::Stream *stream;
			MRNStream(NetPtr& net, int upTransFilter, int upSyncFilter, int downSyncFilter) :
				stream(net->new_Stream(net->get_BroadcastCommunicator(),
					upTransFilter, upSyncFilter, downSyncFilter)) {

				if (stream == nullptr) {
					throw std::runtime_error("MRNet new_Stream() failed.");
				}
			}

			void setTimeout(unsigned int milliseconds) {
				stream->set_FilterParameters(MRN::FILTER_UPSTREAM_SYNC, "%ud", milliseconds);
			}

			void sendReady(int tag, size_t numPEs) {
				if ((stream->send(tag, "%ud", (unsigned int)numPEs) < 0) ||
				    (stream->flush() == -1)) {
					throw std::runtime_error("MRNet Stream::send failed.");
				}
			}
		};

		int numPEs = cti_getNumAppPEs(appId);
		
		// set up the synchronous command stream
		{ MRNStream cmd_stream(net, sum_filter_id, MRN::SFILTER_WAITFORALL, MRN::TFILTER_NULL);
			num_mrnet_nodes = comm->get_EndPoints().size();
			cmd_stream.sendReady(APG_CMD_READY, numPEs);
		}

		// set up the asynchronous message streams
		{ MRNStream msg_stream(net, aggregate_filter_id, MRN::SFILTER_TIMEOUT, MRN::TFILTER_NULL);
			msg_stream.setTimeout(1000);
			msg_stream.sendReady(APG_MSG_READY, numPEs);
		}
		{ MRNStream leak_stream(net, leak_filter_id, MRN::SFILTER_TIMEOUT, MRN::TFILTER_NULL);
			leak_stream.setTimeout(1000);
			leak_stream.sendReady(APG_LEAK_READY, numPEs);
		}
		{ MRNStream count_stream(net, pair_sum_filter_id, MRN::SFILTER_TIMEOUT, MRN::TFILTER_NULL);
			count_stream.setTimeout(1000);
			count_stream.sendReady(APG_COUNT_READY, numPEs);
		}
		{ MRNStream summary_stream(net, summary_filter_id, MRN::SFILTER_TIMEOUT, MRN::TFILTER_NULL);
			summary_stream.setTimeout(1000);
			summary_stream.sendReady(APG_SUMMARY_READY, numPEs);
		}

		num_daemons = cti_getNumAppNodes(appId);

		// Wait for finish to become true and check for block timeouts
		std::ostream output_stream(output_buf);
		auto lastAppCheck = std::chrono::system_clock::now();
		while (!finish) {
			std::unique_lock<std::mutex> lck(finish_mtx);
			finish_cv.wait_for(lck, std::chrono::duration<double>(0.5));
			if (finish) {
				break;
			}

			{ std::lock_guard<std::mutex> mtx_lck(mtx);
				while(const auto& evicted = masterErrorAgg->evict()) {
					print_msg(evicted.get(), output_stream);
				}
				while(const auto& evicted = masterLeakAgg->evict()) {
					print_msg(evicted.get(), output_stream);
				}
				// all Summary blocks are output after completion of the run, instead of during
			}

			// Run application status check
			if (std::chrono::system_clock::now() - lastAppCheck >= std::chrono::seconds{5}) {

				// Application exited early
				if (!cti_appIsValid(appId)) {
					fprintf(stderr, "Valgrind4hpc detected early job exit, cleaning up...\n");
					break;
				}

				lastAppCheck = std::chrono::system_clock::now();
			}
		}

	} catch (std::exception& e) {
		std::cerr << argv[0] << ": front end caught exception '" << e.what() << "'" << std::endl;

		ret = 1;
		if (appId != 0) {
			cti_killApp(appId, SIGKILL);
		}
	}

	
	// cleanup - this also cleans up the manifest and session
	if (appId != 0)
	{
		cti_deregisterApp(appId);
	}

	std::ostream output_stream(output_buf);
	if (masterErrorAgg) {
		for (auto it : *masterErrorAgg) {
			print_msg(it, output_stream);
		}
	}

	if (masterLeakAgg) {
		for (auto it : *masterLeakAgg) {
			print_msg(it, output_stream);
		}
	}

	if (masterSummaryAgg) {
		for (auto it : *masterSummaryAgg) {
			print_msg(it, output_stream);
		}
	}

	// If application exited early and there were no errors, don't print summaries
	if (finish || (total_errors > 0)) {
		output_stream << "ERROR SUMMARY: "<< unique_errors << " errors from " << total_errors << " contexts";
		output_stream << " (suppressed " << total_suppressions << ")\n\n";
	}

	// Output generated suppressions

	if (masterSuppressionAgg && (masterSuppressionAgg->size() > 0)) {

		try {

			// Write to provided suppressions file
			if (!args.gen_suppressions_file.empty()) {
				auto suppressionsStream = std::ofstream{};
				suppressionsStream.exceptions(std::ofstream::badbit | std::ofstream::failbit);
				suppressionsStream.open(args.gen_suppressions_file);

				for (auto it : *masterSuppressionAgg) {
					suppressionsStream << it.first << std::endl;
				}
			}

		} catch (std::exception const& ex) {
			output_stream << "Failed to open " << args.gen_suppressions_file << " for writing: "
				<< "(" << ex.what() << ")\n"
				<< "Generated suppressions will be written to this output.\n" << std::endl;
			args.gen_suppressions_file = {};
		}

		// If no file was set, output to stderr
		if (args.gen_suppressions_file.empty()) {
			output_stream << "GENERATED SUPPRESSIONS:\n";

			for (auto it : *masterSuppressionAgg) {
				output_stream << it.first << std::endl;
			}
		}
	}

	output_file.close();

	return ret;
}

static std::unique_ptr<MRN::Network>
BuildNetwork(cti_app_id_t appId, cti_manifest_id_t mid, rank_set_t const& activeRankSet)
{
	// default fanout value
	const unsigned int fanout = 32;

	// use CTI info to populate set of hostnames
	std::set<std::string> hostnameSet;

	// get host info list from CTI
	{ auto hostsList = std::unique_ptr<cti_hostsList_t, std::function<void(cti_hostsList_t*)>>(
		cti_getAppHostsPlacement(appId), cti_destroyHostsList);
		if (hostsList == nullptr) {
			throw std::runtime_error(std::string("CTI Error: ") + cti_error_str());
		}

		// populate hostname set (only the user-selected ranks if applicable)
		for (int i = 0; i < hostsList->numHosts; i++) {
			hostnameSet.insert(hostsList->hosts[i].hostname);
		}
	}

	// get cti hostname and build topo
	std::string topo;
	{ CStrPtr cti_myHost(cti_getHostname(), free);
		if (cti_myHost == nullptr) {
			throw std::runtime_error(std::string("CTI Error: ") + cti_error_str());
		}

		topo = BuildFlatTopo(fanout, std::string(cti_myHost.get()), hostnameSet);
		assert(topo.length() > 0);
	}

	// initialize the mrnet attrs for FE instantiation
	const std::map<std::string,std::string> mrnet_attrs {
		{"CRAY_CTI_APPID", std::to_string(appId)},
		{"CRAY_CTI_MID",   std::to_string(mid)}
	};

	// fill in backend daemon args
	OutgoingArgv<BackendArgv> backendArgv("valgrind4hpc_daemon");
	using BA = BackendArgv;

	if (activeRankSet.any() && !activeRankSet.all()) {
		// only pass this argument if there are ranks set
		std::string activeRankString;
		boost::to_string(activeRankSet, activeRankString);
		backendArgv.add(BA::ActiveRankSet, activeRankString);
	}
	backendArgv.add(BA::QueueKey, std::to_string(key));
	if (mpi_binary) { backendArgv.add(BA::BinaryUsesMPI); }
	if (no_stacktrace_mode) { backendArgv.add(BA::NoStacktraces); }
	if (no_timeout_mode) { backendArgv.add(BA::NoTimeout); }

	sleep(5);
	auto rawBackendArgv = (const char**)backendArgv.get();
	return std::unique_ptr<MRN::Network>(
		// MRNet adds the argv[0] automatically, so backendArgv.get() + 1 as the argv argument.
		MRN::Network::CreateNetworkFE(topo.c_str(), rawBackendArgv[0], rawBackendArgv + 1, &mrnet_attrs, true, true)
	);
}
