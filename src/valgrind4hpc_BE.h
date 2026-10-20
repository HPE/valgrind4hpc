/******************************************************************************\
 * valgrind4hpc_BE.h - Tool daemon portion of parallel valgrind tool.
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

#ifndef _VALGRIND4HPC_BE_H
#define _VALGRIND4HPC_BE_H

#include <boost/functional/hash.hpp>

#define BYTES_UNDEFINED -1
#define BLOCKS_UNDEFINED -1

class ValgrindBlock
{
public:
	enum ExtraTag : int {
		Exit = -1,
		Error = -2
	};
private:
	std::string msg;
public:
	int rank;
	int tag;
	const size_t tidx;
	const pid_t pid;
	ValgrindBlock(size_t tidx_, pid_t pid_, int tag_, std::string msg_) :
		 msg(msg_), rank(-1), tag(tag_), tidx(tidx_), pid(pid_) { }
	std::string getMsg() const& { return msg; }
	void setMsg(std::string const& msg_) { msg = msg_; }

	bool operator==(const ValgrindBlock &other) const
	{
		return ((tag == other.tag) && (msg.compare(other.getMsg()) == 0));
	}
};

struct ExitBlock : public ValgrindBlock {
	ExitBlock(size_t tidx_, pid_t pid_) : ValgrindBlock(tidx_, pid_, ExtraTag::Exit, "") {}
};

struct ErrorBlock : public ValgrindBlock {
        ErrorBlock(size_t tidx_, pid_t pid_, std::string what) : ValgrindBlock(tidx_, pid_, ExtraTag::Error, what) {}
};

namespace std {
	template <> struct hash<ValgrindBlock>
	{
		std::size_t operator()(const ValgrindBlock& k) const
		{
			std::size_t seed = 0;
			boost::hash_combine(seed, std::hash<std::string>()(k.getMsg()));
			boost::hash_combine(seed, std::hash<int>()(k.tag));

			return seed;
		}
	};
}

#endif /* _APGRIND_BE_H */

