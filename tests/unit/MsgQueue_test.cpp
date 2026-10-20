#include <future>
#include <unordered_set>

#include "MsgQueue_test.hpp"

/* message queue tests */

// Tests the message queue push / pop
TEST_F(MsgQueueTest, MsgQueuePush)
{
	// set up queue elements
	std::unordered_set<std::string> testElems{};
	for (int i = 0; i < 100; i++) {
		testElems.insert(std::to_string(i));
	}

	// to hold the read/write futures
	std::vector<std::future<void>> futures;

	// asynchronously add / read elements from queue
	futures.push_back(std::async(std::launch::async, [&]() {
		for (auto&& elem : testElems) {
			writeQueue.send(MsgQueue::MsgType::SocketInfo, elem);
		}
	}));

	futures.push_back(std::async(std::launch::async, [&]() {
		auto unseenElems = testElems;
		std::string received;

		while (!unseenElems.empty()) {
			// pop queue element and find in element set
			readQueue.recv(received, MsgQueue::MsgType::SocketInfo);
			auto popped = unseenElems.find(received);

			// ensure the queue unseenElems has only been seen once by removing from set
			ASSERT_EQ(popped != testElems.end(), true);
			unseenElems.erase(popped);
		}
	}));

	// queue should be empty after all futures checked
	for (auto&& future : futures) {
		future.get();
	}
}
