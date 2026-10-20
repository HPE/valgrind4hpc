#include <future>
#include <unordered_set>

#include "TSQueue_test.hpp"

/* thread safe queue tests */

// Tests the threadsafe queue push / pop
TEST_F(TSQueueTest, TSQueuePush)
{
	// set up queue elements
	std::unordered_set<int> testElems{};
	for (int i = 0; i < 100; i++) {
		testElems.insert(i);
	}

	// to hold the queue push futures
	std::vector<std::future<void>> futures;

	// asynchronously add elements to queue
	for (auto&& elem : testElems) {
		futures.push_back(std::async(std::launch::async, [&]() {
			q.push(elem);
		}));
	}

	// each future should correspond to a unique element added to queue
	for (auto&& future : futures) {
		// ensure at least one element added to queue
		future.get();

		// pop queue element and find in element set
		auto popped = testElems.find(q.pop());

		// ensure the queue element has only been seen once by removing from set
		ASSERT_EQ(popped != testElems.end(), true);
		testElems.erase(popped);
	}

	// queue should be empty after all futures checked
	EXPECT_EQ(testElems.size(), 0u);
}
