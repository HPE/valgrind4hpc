#pragma once

#include "gtest/gtest.h"

#include "utils/TSQueue.hpp"

/* thread safe queue test fixtures */

// The fixture for testing a threadsafe queue
class TSQueueTest : public ::testing::Test
{
	protected:
		TSQueue<int> q;

		TSQueueTest()
			: q{}
		{}

		~TSQueueTest() override
		{}
};
