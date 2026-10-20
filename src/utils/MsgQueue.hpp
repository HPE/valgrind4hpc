/******************************************************************************\
 * MsgQueue.hpp - Kernel messagequeue helper object
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

#ifndef _MSGQUEUE_HPP
#define _MSGQUEUE_HPP

#define MSG_QUEUE_SIZE			256

#include <sys/types.h>
#include <sys/msg.h>
#include <sys/ipc.h>

class MsgQueue {
public:
	enum MsgType {
		SocketInfo = 1,
		BinPath,
		TmpDir,
		Shutdown
	};

	struct msg_buffer {
		long mtype;
		char mtext[MSG_QUEUE_SIZE + 1];
	};

	static constexpr const char* DestroyOnShutdown = "destroy";
	static constexpr const char* KeepOnShutdown = "keep";
private:
	key_t key;
	int q_id;

	// make MsgQueue moveable but not copyable
	MsgQueue(const MsgQueue&) = delete;
	MsgQueue& operator=(const MsgQueue&) = delete;
public:
	MsgQueue(MsgQueue&& other) noexcept
		: key{other.key}
		, q_id{other.q_id}
	{
		other.q_id = -1;
	}

	MsgQueue(key_t k)
		: key{k}
		, q_id{msgget(key, IPC_CREAT | 0600)}
	{
		if (q_id < 0) {
			throw std::runtime_error("failed to get message queue");
		}
	}

	int deregister()
	{
		if (q_id < 0) {
			throw std::runtime_error("message queue has already been deregistered");
		}

		int ret = msgctl(q_id, IPC_RMID, NULL);
		q_id = -1;
		return ret;
	}

	int send(MsgType type, std::string const& msg)
	{
		if (msg.length() > MSG_QUEUE_SIZE) {
			throw std::runtime_error(
				std::string("string too long for message queue (len ") +
				std::to_string(msg.length()) + ")");
		}

		struct msg_buffer msg_buf;

		msg_buf.mtype = type;

		strncpy(msg_buf.mtext, msg.c_str(), MSG_QUEUE_SIZE);
		msg_buf.mtext[MSG_QUEUE_SIZE] = '\0';

		return msgsnd(q_id, &msg_buf, strlen(msg_buf.mtext) + 1, 0);
	}
	// return -1 if failure
	// store received text in buf
	int recv(std::string& result, MsgType type)
	{
		struct msg_buffer msg_buf;

		int rcv = msgrcv(q_id, &msg_buf, MSG_QUEUE_SIZE, type, MSG_NOERROR);
		msg_buf.mtext[MSG_QUEUE_SIZE] = '\0';

		result = std::string(msg_buf.mtext);

		return rcv;
	}
};

#endif
