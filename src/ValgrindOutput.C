/******************************************************************************\
 * ValgrindOutput.C - Valgrind error block output object
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

#include "ValgrindOutput.hpp"

/* valgrindoutput xml info extraction */

/* the valgrind xml error ordering:
   - Preamble: kind, what...
   - Primary error <stack> with list of <frame>s
   - Optional <auxwhat>
   - Optional auxillary <stack> with list of <frame>s
   Again, we need to keep track of what we've seen so far, as valgrind 
   relies on the ordering above to distinguish primay/aux errors. */

ValgrindOutput::ValgrindError::ValgrindError(
	ValgrindOutput::Protocol protocol, std::string const& targetExecutable,
		PtreeVal const& ov) :
	errorStage(Preamble),
	what(ov.second.get<std::string>("xwhat.text", "")),
	kind(ov.second.get<std::string>("kind", "")) {

	/* extract basic error information */
	if (protocol == ValgrindOutput::Protocol::Memcheck) {
		if (!what.empty()) {
			leaked.first = ov.second.get<size_t>("xwhat.leakedbytes", 0);
			leaked.second = ov.second.get<size_t>("xwhat.leakedblocks", 0);
		} else {
			what = ov.second.get<std::string>("what", "");
			leaked.first = ov.second.get<size_t>("leakedbytes", 0);
			leaked.second = ov.second.get<size_t>("leakedblocks", 0);
		}
	} else {
		if (what.empty()) {
			what = ov.second.get<std::string>("what", "");
		}
	}

	/* create stack frame info objects */
	errorStage = Stack;
	BOOST_FOREACH (PtreeVal const& ev, ov.second) {
		if (ev.first == "stack") {
			BOOST_FOREACH (PtreeVal const& fv, ev.second) {
				if (errorStage == Stack) {
					stack.emplace_back(fv, targetExecutable);
				} else {
					auxStack.emplace_back(fv, targetExecutable);
				}
			}
		} else if (ev.first == "auxwhat") {
				auxWhat = ev.second.get_value<std::string>();
			errorStage = AuxStack;
		}
	}
}

ValgrindOutput::ValgrindSignal::ValgrindSignal(
	ValgrindOutput::Protocol protocol, std::string const& targetExecutable,
		PtreeVal const& ov) :
	sigNo(ov.second.get<std::string>("signo", "")),
	sigName(ov.second.get<std::string>("signame", "")) {

	/* create stack frame info objects */
	BOOST_FOREACH (PtreeVal const& ev, ov.second) {
		if (ev.first == "stack") {
			BOOST_FOREACH (PtreeVal const& fv, ev.second) {
				stack.emplace_back(fv, targetExecutable);
			}
		}
	}
}

/* valgrinderror formatters */

// formatting helpers
std::ostream& frameOut(std::ostream& os, const ValgrindFrame& f) {
	os	<< f.fn << " (in " << f.file
		<< (!f.line.empty() ? ":" + f.line : "") << ")";
	return os;
}

std::ostream& stackOut(std::ostream& os, const std::vector<ValgrindFrame>& stack) {
	bool firstFrame = true;
	for (const auto& f : stack) {
		if (firstFrame) {
			os << "  at ";
			firstFrame = false;
		} else {
			os << "  by ";
		}
		frameOut(os, f) << "\n";
	}
	return os;
}

std::string ValgrindOutput::ValgrindError::getString(UseStacktraces useStacktraces) {
	if (!formattedMessage.empty()) { return formattedMessage; }

	std::stringstream ss;

	/* main stack */

	// trim out number of blocks lost
	{ size_t ind = what.find("blocks are definitely lost");
		if (ind != std::string::npos) {
			what = what.substr(0, ind+26);
		}
	}
	ss << what << "\n";
	if (useStacktraces == FullTraces) { stackOut(ss, stack); }

	/* aux stack */

	if (!auxWhat.empty()) {
		// trim out raw address
		if (auxWhat.find("Address 0x") != std::string::npos) {
			size_t ind = auxWhat.find("0x");
			size_t len = auxWhat.find(" ", ind);
			if (len != std::string::npos) {
				auxWhat = auxWhat.substr(0, ind) + auxWhat.substr(len + 1);
			}
		}

		ss << auxWhat << "\n";
		if (useStacktraces == FullTraces) { stackOut(ss, auxStack); }
	}

	formattedMessage = ss.str();
	return formattedMessage;
}

std::string ValgrindOutput::ValgrindSignal::getString() {
	if (!formattedMessage.empty()) { return formattedMessage; }

	std::stringstream ss;

	ss	<< "VALGRIND INTERNAL ERROR: Valgrind received a signal "
		<< sigNo << "(" << sigName << ") - exiting" << "\n";

	stackOut(ss, stack);

	formattedMessage = ss.str();
	return formattedMessage;
}

/* valgrindoutput xml info extraction */

void ValgrindOutput::readPreamble(const Ptree& pt) {
	if (pid == 0) { pid = pt.get<pid_t>("pid", 0); }

	if (ppid == 0) { ppid = pt.get<pid_t>("ppid", 0); }

	if (protocol == Protocol::Undefined) {
		std::string toolName = pt.get<std::string>("protocoltool", "");
		if (!toolName.empty()) {
			if (toolName.compare("memcheck") == 0) {
				protocol = Protocol::Memcheck;
			} else if (toolName.compare("helgrind") == 0) {
				protocol = Protocol::Helgrind;
			} else if (toolName.compare("drd") == 0) {
				protocol = Protocol::Drd;
			} else if (toolName.compare("exp-sgcheck") == 0) {
				protocol = Protocol::ExpSgcheck;
			} else {
				throw std::runtime_error(("received an invalid protocol from pid " + std::to_string(pid) + ": " + toolName).c_str());
			}
		}
	}

	if (targetExecutable.empty()) {
		targetExecutable = pt.get<std::string>("args.argv.exe", "");
	}

	if ((protocol != Protocol::Undefined) && (pid > 0) && (ppid > 0) &&
		!targetExecutable.empty()) {
		// preamble info is complete, backend should update its data structures
		outputStage = Stage::Errors;
	}
}

MaybeBlock ValgrindOutput::readMessage(const Ptree& pt, int errorTag) {
	BOOST_FOREACH(PtreeVal const& ov, pt) {
		if (ov.first == "error") {
			/* create error info object */
			ValgrindError errorInfo(protocol, targetExecutable, ov);

			/* update total leak info */
			if (errorInfo.leaked.first > 0) {
				leakInfo["Leak"] += errorInfo.leaked;
				leakInfo[errorInfo.kind] += errorInfo.leaked;
			}

			/* return constructed block */
			return MaybeBlock(ValgrindBlock(tidx, pid, errorTag, errorInfo.getString(useStacktraces)));
		} else if ((ov.first == "errorcounts") || (ov.first == "suppcounts")) {
			BOOST_FOREACH (PtreeVal const& cv, ov.second) {
				/* update error / suppression counts */
				if (cv.first == "pair") {
					counts[ov.first] += cv.second.get<size_t>("count", 0);
					contexts[ov.first]++;
				}
			}
		} else if (ov.first == "status") {
			/* done with errors, start reading leak totals */
			std::string status = ov.second.get<std::string>("state", "");
			if (!status.compare("FINISHED")) {
				outputStage = Stage::Leaks;
			}
		} else if (ov.first == "fatal_signal") {
			/* create signal info object */
			ValgrindSignal sigInfo(protocol, targetExecutable, ov);

			/* return constructed block */
			return MaybeBlock(ValgrindBlock(tidx, pid, APG_MSG, sigInfo.getString()));

		} else if (ov.first == "vgdb") {
			auto ss = std::stringstream{};

			// Add placeholders that will be filled in with information from CTI
			ss << "Entered VGDB mode. To attach to with GDB4hpc: start GDB4hpc and run\n"
			   << "  attach $a --vgdb=%command_file_path% %job_id%\n"
               << "To attach to this rank only: SSH to node `%node_name%`, start GDB, and run\n"
			   << "  target remote | %vgdb_path%"
			   << " --vgdb-prefix=" << ov.second.get<std::string>("prefix")
			   << " --vgdb-host=" << ov.second.get<std::string>("host")
			   << " --vgdb-user=" << ov.second.get<std::string>("user")
			   << " --pid=" << pid;

			return MaybeBlock(ValgrindBlock(tidx, pid, APG_VGDB, ss.str()));

		} else if (ov.first == "suppression") {
			auto ss = std::stringstream{};

			// Construct suppression block
			ss << "{\n";
			for (auto&& child : ov.second) {
				if (child.first == "sname") {
					ss << "   <" << child.second.get_value<std::string>() << ">\n";
				} else if ((child.first == "skind") || (child.first == "skaux")) {
					ss << "   " << child.second.get_value<std::string>() << "\n";
				} else if (child.first == "sframe") {
					for (auto&& frame : child.second) {
						ss << "   " << frame.first << ":" << frame.second.get_value<std::string>() << "\n";
					}
				}
			}
			ss << "}";

			return MaybeBlock(ValgrindBlock(tidx, pid, APG_SUPPRESSION, ss.str()));
		}
	}

	return boost::none;
}

/* valgrindoutput formatters */

std::string ValgrindOutput::getSummary() {
	if (!formattedMessage.empty()) { return formattedMessage; }

	std::stringstream ss;

	ss	<< "HEAP SUMMARY:\n  in use at exit: " << leakInfo["Leak"].first
		<< " bytes in " << leakInfo["Leak"].second << " blocks\n\n";
	
	if(leakInfo["Leak"].second == 0) {
		ss << "All heap blocks were freed -- no leaks are possible\n";
	} else {
		ss	<< "LEAK SUMMARY:\n"
			<< "   definitely lost: " << leakInfo["Leak_DefinitelyLost"].first
			<< " bytes in " << leakInfo["Leak_DefinitelyLost"].second << " blocks\n"
			<< "   indirectly lost: " << leakInfo["Leak_IndirectlyLost"].first
			<< " bytes in " << leakInfo["Leak_IndirectlyLost"].second << " blocks\n"
			<< "     possibly lost: " << leakInfo["Leak_PossiblyLost"].first
			<< " bytes in " << leakInfo["Leak_PossiblyLost"].second << " blocks\n"
			<< "   still reachable: " << leakInfo["Leak_StillReachable"].first
			<< " bytes in " << leakInfo["Leak_StillReachable"].second << " blocks\n";
	}
	formattedMessage = ss.str();

	return formattedMessage;
}
