#pragma once

#include <unistd.h>

#include "gtest/gtest.h"

#include "utils/MsgQueue.hpp"

// The fixture for testing a kernel message queue
class MsgQueueTest : public ::testing::Test
{
	protected:
		key_t queueKey;
		MsgQueue readQueue, writeQueue;

		MsgQueueTest()
			: queueKey{getpid()}
			, readQueue{queueKey}
			, writeQueue{queueKey}
		{}

		~MsgQueueTest() override
		{
			writeQueue.deregister();
		}
};
