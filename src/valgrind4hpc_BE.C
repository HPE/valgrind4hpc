/******************************************************************************\
 * valgrind4hpc_BE.C - Tool daemon portion of parallel valgrind tool.
 *
 * Copyright 2015,2020 Hewlett Packard Enterprise Development LP..
 *
 * Unpublished Proprietary Information.
 * This unpublished work is protected to trade secret, copyright and other laws.
 * Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
 * no part of this work or its content may be used, reproduced or disclosed
 * in any form.
 *
 * $HeadURL$
 * $Date$
 * $Rev$
 * $Author$
 *
 ******************************************************************************/

// C interfaces
#include <cstdlib>
#include <cassert>
#include <cerrno>
#include <cstring>
#include <ctime>

// strings & IO
#include <iostream>
#include <sstream>
#include <string>

// containers
#include <unordered_map>
#include <vector>

// threading
#include <thread>
#include <atomic>
#include <mutex>
#include <condition_variable>

// exceptions
#include <exception>
#include <stdexcept>

// boost
#include <boost/dynamic_bitset.hpp>
#include <boost/property_tree/xml_parser.hpp>
#include <boost/algorithm/string.hpp>

// MRNet / CTI
#include "mrnet/MRNet.h"
#include "common_tools_be.h"

// valgrind4hpc definitions
#include "valgrind4hpc_defs.h"
#include "valgrind4hpc_protocol.h"
#include "valgrind4hpc_BE.h"
#include "ArgvDefs.hpp"

// aggregator implementations
#include "valgrind4hpc_aggregator.h"

// helper includes
#include "utils/Socket.hpp"     // socket / bind / listen / accept RAII
#include "utils/FdBuf.hpp"      // turn a file descriptor into a streambuf
#include "utils/XmlChunker.hpp" // split an istream into XML blocks
#include "utils/TSQueue.hpp"    // threadsafe queue
#include "utils/MsgQueue.hpp"   // kernel message queue object
#include "utils/make_unique.hpp"// shim make_unique for GCC 4.8 for CS

// valgrind xml output parsing
#include "ValgrindOutput.hpp"

#define COMPONENT_NAME "v4hBackend"
#include "timed_logging.hpp"

// global variables

using BlockRankPair = std::pair<ValgrindBlock, rank_set_t>;

class JoinThread {
	std::thread thread;

public:
	template <typename FnType, typename... Args>
	JoinThread(FnType fn, Args&&... args) : thread(fn, std::forward<Args>(args)...) {}
	JoinThread(JoinThread&& moved) : thread(std::move(moved.thread)) {}

	~JoinThread() { if (thread.joinable()) { thread.join(); } }
	void join() { thread.join(); }
};

class DetachedThread {
	std::thread thread;

public:
	template <typename FnType, typename... Args>
	DetachedThread(FnType fn, Args&&... args) : thread(fn, std::forward<Args>(args)...) {
		thread.detach();
	}
	DetachedThread(DetachedThread&& moved) : thread(std::move(moved.thread)) {}
};

// synchronization between listener threads when accepting connections
static std::mutex listener_thread_mtx;

// synchronization between worker threads when storing parsed blocks
static std::mutex worker_thread_mtx;
static std::condition_variable worker_thread_cv;
static TSQueue<ValgrindBlock> blocks;

// thread / async exception pointers
static std::exception_ptr listener_exception = nullptr;

// information every thread needs
static bool mpi_binary = true;
static size_t num_starters = 0;
static bool noStacktraces = false;

// MRNet handle definitions
using NetHandle = std::unique_ptr<MRN::Network, std::function<void(MRN::Network*)>>;
auto netHandleDeleter = [](MRN::Network *ptr){ ptr->waitfor_ShutDown(); delete ptr; };
NetHandle netHandle;

class MRNStreamHandle {
	MRN::Stream* stream;
public:
	MRNStreamHandle(MRN::Stream* stream_) :
		stream(stream_) {}

	template <typename... Params>
	void send(Params&&... msgs) {
		if (stream->send(std::forward<Params>(msgs)...) < 0) {
			throw std::runtime_error("Failed to send message");
		}

		if (stream->flush() < 0) {
			throw std::runtime_error("Failed to flush stream");
		}
	}

	void sendAggregate(int tag, std::string const& msg) {
		std::vector<const char*> msgData{msg.c_str()};
		return send(tag, APG_AGGREGATE_FS, msgData.data(), 1);
	}

	~MRNStreamHandle() {
		sendAggregate(APG_EXIT, "1");
	}
};

// MRNet-related definitions
static const size_t numMRNStreams = 5;

using CmdStreamPtr = std::unique_ptr<MRNStreamHandle, std::function<void(MRNStreamHandle*)>>;
auto cmdStreamPtrDeleter = [](MRNStreamHandle* ptr) { ptr->send(APG_EXIT, "%ud", 1); };

using TagStreamMap = std::unordered_map<int, std::unique_ptr<MRNStreamHandle>>;

static const std::unordered_map<int, int> readyTagMap {
	{APG_MSG,               APG_MSG_READY},
	{APG_ERROR_COUNT,       APG_COUNT_READY},
	{APG_SUPPRESSION_COUNT, APG_COUNT_READY},
	{APG_SUMMARY,           APG_SUMMARY_READY},
	{APG_LEAK,              APG_LEAK_READY},
	{APG_SUPPRESSION,       APG_MSG_READY}
};

// use CTI and its quirks to fetch pids and rank information
class RankRegistry {
	using CtiPidList = std::unique_ptr<cti_pidList_t, std::function<void(cti_pidList_t*)>>;

	std::unordered_map<pid_t, pid_t> valgrind_to_starter_pid;
	std::unordered_map<pid_t, int> pid_to_rank;

public:
	rank_set_t ranks;

	RankRegistry() {}

	size_t addFromCti() {
		// ALPS: causes stall on MPI apps and hang on non-MPI apps (tries to read pmi_attribs)
		CtiPidList pids(cti_be_findAppPids(), cti_be_destroyPidList);
		if (pids == nullptr) {
			throw std::runtime_error("Unable to obtain app pids");
		}
		log("cti_be_findAppPids returned %d pids\n", pids->numPids);
		auto max_rank = size_t{0};
		for (int i = 0; i < pids->numPids; ++i) {
			max_rank = std::max(max_rank, (size_t)pids->pids[i].rank);
		}
		ranks.resize(max_rank + 1);
		for (int i = 0; i < pids->numPids; ++i) {
			pid_to_rank.emplace(pids->pids[i].pid, pids->pids[i].rank);
			log("adding pid %d to pids_to_ranks\n", pids->pids[i].pid);
			ranks.set(pids->pids[i].rank);
		}

		return pids->numPids;
	}

	void insert(pid_t pid, pid_t ppid) {
		if (!mpi_binary) {
			pid_to_rank.emplace(pid, pid_to_rank.size());
		}
		valgrind_to_starter_pid.emplace(pid, ppid);
	}

	int getRank(pid_t pid) {
		auto rank_it = pid_to_rank.find(pid);
		if (rank_it == pid_to_rank.end()) {

			// check to see if we recieved a message from a child pid
			auto pid_it = valgrind_to_starter_pid.find(pid);
			if (pid_it == valgrind_to_starter_pid.end()) {
				// no, just an invalid message to begin with
				return -1;
			}

			// swap the ranks' pids, GetAppPids gave us valgrind4hpc_starter pids
			for (auto it = valgrind_to_starter_pid.begin(); it != valgrind_to_starter_pid.end(); it++) {
				int newrank = pid_to_rank.find(it->second)->second;
				pid_to_rank.emplace(it->first, newrank);
			}
			valgrind_to_starter_pid.clear();

			rank_it = pid_to_rank.find(pid);
		}
		
		return rank_it->second;
	}

	size_t getNumConnected() const { return valgrind_to_starter_pid.size(); }
};
std::unique_ptr<RankRegistry> rankRegistry;

static void sendBlockRankMsg(TagStreamMap& streamHandles, const BlockRankPair& brp) {
	const ValgrindBlock& block = brp.first;
	const rank_set_t&    rankset = brp.second;

	auto it = readyTagMap.find(block.tag);
	if (it == readyTagMap.end()) {
		throw std::runtime_error("invalid incoming tag " + std::to_string(block.tag));
	}
	auto& streamPtr = streamHandles[it->second];
	if (streamPtr == nullptr) {
		throw std::runtime_error("sent on uninitialized stream");
	}

	std::string rankset_str;
	boost::to_string(rankset, rankset_str);
	log("sending %s\n", (rankset_str + " \n" + block.getMsg()).c_str());
	streamPtr->sendAggregate(block.tag, rankset_str + " \n" + block.getMsg());
}

static void sendErrorMsg(TagStreamMap& streamHandles, std::string const& what) {
	log("sending exception: %s\n", what.c_str());
	if (streamHandles.find(APG_MSG_READY) != streamHandles.end()) {
		streamHandles[APG_MSG_READY]->sendAggregate(APG_ERROR, what);
	}
}


void
socket_worker(int fd, int tidx)
{
	const std::string rootTagName = "valgrindoutput";

	// create the istream from socket fd
	FdBuf pipeInBuf(fd);
	std::istream pipein(&pipeInBuf);
	XmlChunker chunker(pipein);

	using OutputStage = ValgrindOutput::Stage;
	OutputStage lastStage = OutputStage::Uninitialized;
	pid_t client_tidx = 0; pid_t client_pid = 0;

	try {
		// ignore opening <?xml ... ?>
		for (std::string possibleXmlHeader = chunker.readTag();
			possibleXmlHeader.at(0) != '?'; possibleXmlHeader = chunker.readTag()) {
		}

		// validate opening <valgrindoutput>
		{ std::string possibleRootTag = chunker.readTag();
			if (possibleRootTag.compare(rootTagName)) {
				log("invalid root tag: %s\n", possibleRootTag.c_str());
				throw std::runtime_error("expected first tag to be <valgrindoutput>");
			}
		}

		// start filling in ValgrindOutput object
		ValgrindOutput v(tidx, noStacktraces ? ValgrindOutput::NoTraces : ValgrindOutput::FullTraces);
		lastStage = OutputStage::Preamble;

		for (std::string blockContent = chunker.readBlock();
			!blockContent.empty(); blockContent = chunker.readBlock()) {

			// did we get the closing root tag?
			if (!blockContent.compare("/" + rootTagName)) {
				break;
			}

			// parse the xml block as boost ptree and add to list
			boost::property_tree::ptree pt;
			{ std::stringstream ss;
				ss << blockContent;
				read_xml(ss, pt);
			}

			// delegate reading of ptree to ValgrindBlock object
			if (boost::optional<ValgrindBlock> maybeBlock = v.readPtree(pt)) {

				// Process VGDB block
				auto msg = maybeBlock->getMsg();
				if (maybeBlock->tag == APG_VGDB) {

					// Replace backend path placeholders in message
					if (auto rawAppId = CStrPtr{cti_be_getAppId(), free}) {
						boost::replace_all(msg, "%job_id%", rawAppId.get());
					}
					if (auto rawBeDir = CStrPtr{cti_be_getRootDir(), free}) {
						auto beDir = std::string{rawBeDir.get()};
						boost::replace_all(msg, "%vgdb_path%", beDir + "/bin/vgdb");
						boost::replace_all(msg, "%command_file_path%", beDir + "/vgdb-commands");
					}
					if (auto rawNodeName = CStrPtr{cti_be_getNodeHostname(), free}) {
						boost::replace_all(msg, "%node_name%", rawNodeName.get());
					}

					// Split VGDB block into two, one for GDB4hpc that will get aggregated
					// from all ranks, and one with the rank-unique instructions
					auto rankInstructionsAt = msg.find("To attach to this rank only");
					if (rankInstructionsAt != std::string::npos) {

						// Create new rank-specific block
						auto rankSpecificBlock = maybeBlock.get();
						rankSpecificBlock.setMsg(msg.substr(rankInstructionsAt));
						log("Complete Block: %s\n", rankSpecificBlock.getMsg().c_str());
						blocks.push(rankSpecificBlock);

						// Save GDB4hpc instructions
						maybeBlock->tag = APG_MSG;
						msg = msg.substr(0, rankInstructionsAt);
					}

					maybeBlock->setMsg(msg);
				}

				log("Complete Block: %s\n", msg.c_str());
				blocks.push(maybeBlock.get());
			}

			// check for output stage changes
			if (lastStage != v.getStage()) {
				switch (v.getStage()) {
				case OutputStage::Errors: // done with preamble, update locations that need PID/PPID
					client_tidx = v.getTidx();
					client_pid  = v.getPid();
					{ std::lock_guard<std::mutex> lck(worker_thread_mtx);
						rankRegistry->insert(v.getPid(), v.getPpid());
					}
					worker_thread_cv.notify_one();
					break;
				case OutputStage::Leaks: // TODO: done with errors, tell main thread to flush aggregators
					break;
				case OutputStage::Preamble: // shouldn't get this
				default:
					throw std::logic_error("invalid ValgrindOutput stage");
				}
			}
			lastStage = v.getStage();
		}

		// push the summary and count blocks
		blocks.emplace(client_tidx, client_pid, APG_ERROR_COUNT, std::to_string(v.getErrorCounts()));
		blocks.emplace(client_tidx, client_pid, APG_SUPPRESSION_COUNT, std::to_string(v.getSuppCounts()));
		blocks.emplace(client_tidx, client_pid, APG_SUMMARY, v.getSummary());

		// notify main loop via closing block
		blocks.push(ExitBlock(client_tidx, client_pid));
		log("pid %d pushed closing block\n", client_pid);
	} catch (std::exception const& ex) {
		// create error message
		std::stringstream err_msg;
		if (lastStage == OutputStage::Uninitialized) {
			err_msg << "before Valgrind header was successfully parsed: '";
		} else {
			err_msg << "during parsing of Valgrind output: '";
		}
		err_msg << ex.what() << "'" << std::endl;

		// push block to main thread
		auto const err_str = err_msg.str();
		log("error block: %s\n", err_str.c_str());
		blocks.push(ErrorBlock(client_tidx, client_pid, err_str));
	}

	// shutdown the socket
	{ std::string consume;
		shutdown(fd, SHUT_RDWR);
		while (std::getline(pipein, consume)) {}
	}
}

void
consumer_worker(int fd) {
	char c;
	while (read(fd, &c, 1) > 0) {}
	shutdown(fd, SHUT_RDWR);
	close(fd);
}

// Thread to create and listen for loopback
void
socket_listener(Socket& sock, int queueKey) {
	std::vector<DetachedThread> worker_threads;

	try {
		std::string addressInfoMessage;
		{ std::stringstream ss;
			ss << sock.getAddress() << ":" << sock.getPort();
			addressInfoMessage = ss.str();
		}

		size_t num_starters = cti_be_getNodePEs();
		log("socket listener got %zu starters from CTI\n", num_starters);

		{ MsgQueue msgQueue(queueKey);
			for (size_t i = 0; i < num_starters; i++) {
				// send the socket info and binpath to starter
				if ((msgQueue.send(MsgQueue::MsgType::SocketInfo, addressInfoMessage) < 0) ||
					(msgQueue.send(MsgQueue::MsgType::BinPath,    cti_be_getBinDir()) < 0) ||
					(msgQueue.send(MsgQueue::MsgType::TmpDir,     cti_be_getTmpDir()) < 0)) {
					log("socket msgsnd failed: %s\n", strerror(errno));
					throw std::runtime_error("msgsnd failed");
				}
			}
		}

		while (worker_threads.size() < num_starters) {
			int wfd = sock.accept();
			log("accepted new connection\n");

			// create a new detached worker thread to handle the connection
			// note: make sure to use a different mutex than the main thread.
			// otherwise this is serial and the valgrinds don't like it!
			{ std::lock_guard<std::mutex> wtl(listener_thread_mtx);
				worker_threads.emplace_back(socket_worker, wfd, worker_threads.size());
			}
		}

		// consume input from valgrind children that escape --child-silent-after-fork
		for (int fd = sock.accept(); fd >= 0; fd = sock.accept()) {
			log("accepted extra connection\n");
			DetachedThread consumer_thread(consumer_worker, fd);
		}

	} catch (const std::exception& ex) {
		listener_exception = std::make_exception_ptr(ex);
	}
}


static void shutdownStarters(int queueKey) {
	MsgQueue msgQueue(queueKey);

	for (size_t i = 0; i < num_starters; i++) {
		std::string message = MsgQueue::KeepOnShutdown;
		if (i == num_starters - 1) {
			message = MsgQueue::DestroyOnShutdown;
		}

		if (msgQueue.send(MsgQueue::MsgType::Shutdown, message) < 0) {
			log("msgsnd shutdown failed");
			throw std::runtime_error("msgsnd shutdown failed");
		}
	}
}

static void log_terminate()
{
	if (auto eptr = std::current_exception()) {
		try {
			std::rethrow_exception(eptr);
		} catch(const std::exception& e) {
			log("Uncaught exception: %s\n", e.what());
		}
	}
	globals::logFile.reset();

	std::abort();
}

int
main(int argc, char** argv)
{
	std::set_terminate(log_terminate);

	// variables that will be initialized from argv
	int queueKey = 0;
	NetHandle netHandle;
	rank_set_t activeRankSet;
	bool noTimeout;

	// parse the backend arguments
	{ IncomingArgv<BackendArgv> parsedArgv(argc, argv);
		using BA = BackendArgv;
		int c; std::string value;
		while (true) {
			std::tie(c, value) = parsedArgv.get_next();
			if (c <= 0) { break; }

			switch (c) {

			case BA::BinaryUsesMPI.val:
				mpi_binary = true;
				break;

			case BA::QueueKey.val:
				queueKey = std::stoi(value);
				break;

			case BA::ActiveRankSet.val:
				activeRankSet = rank_set_t(value);
				break;

			case BA::NoTimeout.val:
				noTimeout = true;
				break;

			case BA::NoStacktraces.val:
				noStacktraces = true;
				break;

			case '?':
			default:
				std::stringstream ss;
				ss << "backend bad arg: '" << (char)c << "'";
				throw std::runtime_error(ss.str());
			}
		}

		// rest of arguments are MRNet argv. copy the arguments and create the network handle
		{ std::vector<char*> mrnetwork_argv;
			// create the argv array
			mrnetwork_argv.push_back(strdup(argv[0]));
			{ auto&& [rest_argc, rest_argv] = parsedArgv.get_rest();
				while (*rest_argv != nullptr) {
					mrnetwork_argv.push_back(strdup(*(rest_argv++)));
				}
			}

			// create network backend handle
			netHandle = NetHandle(
				MRN::Network::CreateNetworkBE(mrnetwork_argv.size(), mrnetwork_argv.data()),
				netHandleDeleter
			);

			// free the argv strings
			for (auto str : mrnetwork_argv) { free(str); }
		}
	}
	if (netHandle == nullptr) {
		throw std::runtime_error("MRNet CreateNetworkBE() failed.");
	}

	// create the rank registry
	rankRegistry = shim::make_unique<RankRegistry>();

	// create MRNet stream handles
	CmdStreamPtr cmdStream;
	TagStreamMap streamHandles;

	// Create VGDB command file
	auto vgdbFile = []() {
		using ResultType = std::unique_ptr<FILE, decltype(&fclose)>;
		if (auto be_root_dir = cti_be_getRootDir()) {
			auto vgdbFilePath = std::string{be_root_dir} + "/vgdb-commands";
			return ResultType{::fopen(vgdbFilePath.c_str(), "a"), ::fclose};
		}
		return ResultType{nullptr, ::fclose};
	}();

	try
	{
		// need to get the synchronous command stream and the asynch message streams
		for (size_t streams = 0; streams < numMRNStreams; streams++)
		{
			int readyTag;
			MRN::PacketPtr pkt;
			MRN::Stream* stream = NULL;

			// recv on any stream - tag will identify which stream it is
			if (netHandle->recv(&readyTag, pkt, &stream) == -1)
			{
				throw std::runtime_error("MRNet recv() failed.");
			}

			if (readyTag == APG_CMD_READY)
			{
				if (cmdStream != nullptr) {
					throw std::runtime_error("MRNet tried to create two cmdStreams");
				}

				// set command stream handle
				cmdStream = CmdStreamPtr(
					new MRNStreamHandle(stream), cmdStreamPtrDeleter
				);

				// get the number of backends from the packet
				{ size_t numPEs;
					pkt->unpack("%ud", &numPEs);
					assert(numPEs > 0);
				}
			} else {
				// non-command stream, is a message stream
				streamHandles[readyTag] = shim::make_unique<MRNStreamHandle>(stream);
			}
		}

		// create the listener socket and thread
		Socket listener_socket;
		JoinThread listener_thread(socket_listener, std::ref(listener_socket), queueKey);

		// send the response to the ready msg
		log("streams set up, sending response\n");
		cmdStream->send(APG_STREAMS_OK, "%ud", 1);

		// register the MRNet event callback
		auto mrnet_event_callback = [](MRN::Event*, void*) {
			// right now any callbacks we get should correspond to exiting
		};
		netHandle->register_EventCallback(MRN::Event::DATA_EVENT, MRN::Event::EVENT_TYPE_ALL, mrnet_event_callback, NULL);
		netHandle->register_EventCallback(MRN::Event::ERROR_EVENT, MRN::Event::EVENT_TYPE_ALL, mrnet_event_callback, NULL);

		log("waiting at startup barrier\n");

		if (mpi_binary) { /*
		  wait for the app to hit the startup barrier - we do not want to
		  process any data from the worker queues until after the startup
		  barrier has passed. The pmi_init() will re-fork processes and some
		  of the workers will go away. We want to ignore those workers that
		  exit.
		*/
			log("waiting for cti to report that all readers have started...\n");

			bool ranksAdded = false;
			auto ctiTask = std::thread([&](){
				rankRegistry->addFromCti();
				ranksAdded = true;
			});
			ctiTask.detach();

			while (!ranksAdded) {
				// check for / propagate listener thread exception
				if (listener_exception != nullptr) {
					std::rethrow_exception(listener_exception);
				}
				usleep(10000);
			}
		} else {
			log("not a parallel binary, assuming started\n");
		}
		log("passed barrier\n");

		num_starters = cti_be_getNodePEs();
		log("main thread got %zu starters from cti\n", num_starters);

		// wait until all valgrinds have reported their pids
		{ std::unique_lock<std::mutex> lck(listener_thread_mtx);
			worker_thread_cv.wait(lck, [&]{
				auto allStartersConnected = (rankRegistry->getNumConnected() == num_starters);
				return allStartersConnected || (listener_exception != nullptr);
			});
			lck.unlock();
		}

		// propagate listener thread exception
		if (listener_exception != nullptr) {
			std::rethrow_exception(listener_exception);
		}

		// create aggregator type based on active ranks / timeout selection
		std::unique_ptr<Aggregator<ValgrindBlock>> message_ranks;

		// don't shut out every rank or use group aggregation unnecessarily
		if (activeRankSet.any() && !activeRankSet.all()) {

			// Get subset of active ranks running on node
			auto localActiveRanks = activeRankSet;
			if (rankRegistry->ranks.size() != localActiveRanks.size()) {
				// It's fine to truncate the active rank bitset,
				// as we only want to use the node's ranks anyway
				localActiveRanks.resize(rankRegistry->ranks.size());
			}
			localActiveRanks &= rankRegistry->ranks;
			message_ranks = shim::make_unique<FullAggregator<ValgrindBlock>>(localActiveRanks);
			auto ss = std::stringstream{};
			readable_ranks(ss, rankRegistry->ranks);
			log("opened new subset aggregator with ranks %s\n", ss.str().c_str());

		} else if (noTimeout) {
			message_ranks = shim::make_unique<FullAggregator<ValgrindBlock>>(rankRegistry->ranks);
			auto ss = std::stringstream{};
			readable_ranks(ss, rankRegistry->ranks);
			log("opened new full aggregator with ranks %s\n", ss.str().c_str());
		} else {
			message_ranks = shim::make_unique<FullTimerAggregator<ValgrindBlock>>(1,
				rankRegistry->ranks);
			auto ss = std::stringstream{};
			readable_ranks(ss, rankRegistry->ranks);
			log("opened new timer aggregator with ranks %s\n", ss.str().c_str());
		}

		// start processing information from the worker_threads' queues
		size_t joined = 0;
		while (joined < num_starters) {
			using MaybeBlockRankPair = boost::optional<BlockRankPair>;

			// Try popping a new block from queue
			if (boost::optional<ValgrindBlock> block = blocks.try_pop()) {
				if (block->rank < 0)
				{
					block->rank = rankRegistry->getRank(block->pid); // we always have the pid_to_rank map filled out by now
					if (block->rank < 0) {
						log("block with type %d from pid %d had invalid rank\n",
							block->tag, block->pid);
						throw std::runtime_error("Got a block from an invalid rank!");
					}
				}

				log("block came from rank %d and has type %d\n", block->rank, block->tag);

				if (block->tag < 0) {
					// thread has notified done
					joined++;

					// determine if finished normally or by error
					if (block->tag == ValgrindBlock::ExtraTag::Exit) {
						log("worker %zu done, %zu left\n", block->tidx, (num_starters - joined));
					} else if (block->tag == ValgrindBlock::ExtraTag::Error) {
						sendErrorMsg(streamHandles, block->getMsg());
						log("worker %zu errored! %zu left\n",  block->tidx, (num_starters - joined));
					}
					continue;
				}

				// Send VGDB blocks immediately
				if (block->tag == APG_VGDB) {

					// Add command to VGDB file
					if (vgdbFile) {

						// Get command from block message
						auto msg = block->getMsg();
						auto target_remote = msg.rfind("target remote");
						if (target_remote != std::string::npos) {
							auto vgdbCommand = msg.substr(target_remote);
							fprintf(vgdbFile.get(), "%d %s\n", block->rank,
								vgdbCommand.c_str());
							fflush(vgdbFile.get());
						}
					}

					auto updated = message_ranks->update(block.get(), block->rank, true);
					updated->first.tag = APG_MSG;
					sendBlockRankMsg(streamHandles, *updated);
					log("Sent single VGDB block\n");
					continue;
				}

				if (MaybeBlockRankPair updated = message_ranks->update(block.get(), block->rank))
				{
					log("block was updated, evicted, has type %d\n", updated->first.tag);
					sendBlockRankMsg(streamHandles, *updated);
				}
			}

			// check for timeout evictions
			while (MaybeBlockRankPair evicted = message_ranks->evict()) {
				log("block was evicted, has type %d\n", evicted->first.tag);
				sendBlockRankMsg(streamHandles, *evicted);
			}
		}

		// no more worker queues to read from, send the rest of the messages
		log("no more worker queues, sending rest of messages\n");
		for (auto it = message_ranks->begin(); it != message_ranks->end(); it++) {
			sendBlockRankMsg(streamHandles, *it);
		}

		// listener socket should stop accepting connections
		listener_socket.close();
		listener_thread.join();

	} catch (const std::exception& ex) {
		// make sure we send shutdown messages to still-live starters
		num_starters = cti_be_getNodePEs();
		shutdownStarters(queueKey);

		sendErrorMsg(streamHandles, ex.what());
		return 1;
	}

	log("sending shutdown messages to starters\n");
	shutdownStarters(queueKey);

	return 0;
}
