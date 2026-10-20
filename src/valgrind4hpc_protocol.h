/******************************************************************************\
 * valgrind4hpc_protocol.h - Communication protocol definitions.
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

#ifndef _VALGRID4HPC_PROTOCOL_H
#define _VALGRID4HPC_PROTOCOL_H

#include <string>
#include <unordered_map>
#include <utility>
#include <vector>
#include <chrono>

#include <iostream>

#include <boost/dynamic_bitset.hpp>

#include "mrnet/Types.h"

#define APG_FIRST				(FirstApplicationTag)
#define APG_CMD_READY			(APG_FIRST+1)
#define APG_MSG_READY			(APG_FIRST+2)
#define APG_COUNT_READY		(APG_FIRST+3)
#define APG_SUMMARY_READY		(APG_FIRST+4)
#define APG_LEAK_READY			(APG_FIRST+5)
#define APG_STREAMS_OK			(APG_FIRST+6)
#define APG_MSG				(APG_FIRST+7)
#define APG_ERROR_COUNT		(APG_FIRST+8)
#define APG_SUPPRESSION_COUNT	(APG_FIRST+9)
#define APG_ERROR				(APG_FIRST+10)
#define APG_EXIT				(APG_FIRST+11)
#define APG_SUMMARY			(APG_FIRST+12)
#define APG_LEAK				(APG_FIRST+13)
#define APG_SOCKET_OK			(APG_FIRST+14)
#define APG_VGDB				(APG_FIRST+15)
#define APG_SUPPRESSION         (APG_FIRST+16)

#define APG_SUM_FS		"%ud"
#define APG_AGGREGATE_FS	"%as"

using CStrPtr = std::unique_ptr<char, std::function<void(char*)>>;
using rank_set_t = boost::dynamic_bitset<uint64_t>;

inline void parse_msg(char *raw_str, std::string *msg, rank_set_t **rank_ptr)
{
	char *off = raw_str;
	char *pch;
	
	// First do the conversions
	// The first entry is the pe bitset. This is terminated by a space.
	pch = strchr(off, ' ');
	if (pch == NULL)
	{
		throw std::runtime_error("Invalid raw string for node!");
	}
	// Convert this to the pe_bs
	std::string pe_str(off, pch-off);

	*rank_ptr = new rank_set_t(pe_str);
	off = pch+1;
	
	// The rest of the string is the message
	pch = strchr(off, '\0');
	msg->operator=(std::string(off, pch-off));

	return;
}

// for error output purposes
class NullBuffer : public std::streambuf
{
public:
	int overflow(int c) { return c; }
};
class NullStream : public std::ostream { public: NullStream() : std::ostream(&m_sb) {} private: NullBuffer m_sb; };

#endif /* _VALGRIND4HPC_PROTOCOL_H */
