#include <string>

#include "valgrind4hpc_aggregator_test.hpp"

/* fullaggregator tests */

// Tests that the full evict function does nothing
TEST_F(FullAggregatorTest, FullEvict)
{
	auto message = std::string{"testing"};

	{ auto maybeEvicted = fullAggregator.evict();
		// expecting nothing evicted
		EXPECT_EQ(maybeEvicted == boost::none, true);
	}
}

// Tests that the full update function only evicts when aggregator full
TEST_F(FullAggregatorTest, FullUpdate)
{
	auto message = std::string{"testing"};

	for (size_t i = 0; i < NUM_RANKS; i++) {
		// insert message into aggregator
		auto maybeEvicted = fullAggregator.update(message, i);

		// if we inserted the last rank:
		if (i == (NUM_RANKS - 1)) {
			// expecting evicted: message and full bitset
			EXPECT_EQ(maybeEvicted->first, message);

			// check bitset
			for (size_t j = 0; j < NUM_RANKS; j++) {
				EXPECT_EQ(maybeEvicted->second[j], true);
			}

		// otherwise, expecting nothing evicted
		} else {
			EXPECT_EQ(maybeEvicted == boost::none, true);
		}
	}
}

// Tests that the full merge function evicts when aggregator full
TEST_F(FullAggregatorTest, FullMerge)
{
	auto message = std::string{"testing"};

	// fill group {0}
	{ auto maybeEvicted = fullAggregator.update(message, 0);
		// expecting nothing evicted
		EXPECT_EQ(maybeEvicted == boost::none, true);
	}

	// create the bitset to merge with
	rank_set_t mergeBitset{NUM_RANKS};

	// fill group {1 ... NUM_RANKS}
	for (size_t i = 1; i < NUM_RANKS; i++) {
		mergeBitset.set(i);
	}

	// perform merge
	{ auto maybeEvicted = fullAggregator.merge(message, mergeBitset);
		// expecting evicted: message and full bitset
		ASSERT_EQ(maybeEvicted != boost::none, true);
		EXPECT_EQ(maybeEvicted->first, message);

		// check bitset
		for (size_t j = 0; j < NUM_RANKS; j++) {
			EXPECT_EQ(maybeEvicted->second[j], true);
		}
	}
}

/* groupaggregator tests */

// Tests that the group evict function does nothing
TEST_F(GroupAggregatorTest, GroupEvict)
{
	auto message = std::string{"testing"};

	{ auto maybeEvicted = firstGroupAggregator.evict();
		// expecting nothing evicted
		EXPECT_EQ(maybeEvicted == boost::none, true);
	}
}

// Tests that the group update function only evicts when group full
TEST_F(GroupAggregatorTest, GroupUpdate)
{
	auto message = std::string{"testing"};

	// fill group {0}
	{ auto maybeEvicted = firstGroupAggregator.update(message, 0);
		// expecting ignore when added to other group aggregator
		EXPECT_EQ(secondGroupAggregator.update(message, 0) == boost::none, true);

		// expecting evicted: message and full bitset
		ASSERT_EQ(maybeEvicted != boost::none, true);
		EXPECT_EQ(maybeEvicted->first, message);

		// check bitset
		EXPECT_EQ(maybeEvicted->second[0], true);
	}

	// fill group {1 ... NUM_RANKS}
	for (size_t i = 1; i < NUM_RANKS; i++) {
		// insert message into aggregator
		auto maybeEvicted = secondGroupAggregator.update(message, i);

		// expecting ignore when added to other group aggregator
		EXPECT_EQ(firstGroupAggregator.update(message, i) == boost::none, true);

		// if we inserted the last rank:
		if (i == (NUM_RANKS - 1)) {
			// expecting evicted: message and full bitset
			ASSERT_EQ(maybeEvicted != boost::none, true);
			EXPECT_EQ(maybeEvicted->first, message);

			// check bitset
			for (size_t j = 1; j < NUM_RANKS; j++) {
				EXPECT_EQ(maybeEvicted->second[j], true);
			}

		// otherwise, expecting nothing evicted
		} else {
			EXPECT_EQ(maybeEvicted == boost::none, true);
		}
	}
}

// Tests that the group merge function evicts when aggregator full
TEST_F(GroupAggregatorTest, GroupMerge)
{
	auto message = std::string{"testing"};

	// fill group {1}
	{ auto maybeEvicted = secondGroupAggregator.update(message, 1);
		// expecting nothing evicted
		EXPECT_EQ(maybeEvicted == boost::none, true);
	}

	// create the bitset to merge with
	rank_set_t mergeBitset{NUM_RANKS};

	// fill group {2 ... NUM_RANKS}
	for (size_t i = 2; i < NUM_RANKS; i++) {
		mergeBitset.set(i);
	}

	// perform merge
	{ auto maybeEvicted = secondGroupAggregator.merge(message, mergeBitset);
		// expecting evicted: message and full bitset
		ASSERT_EQ(maybeEvicted != boost::none, true);
		EXPECT_EQ(maybeEvicted->first, message);

		// check bitset
		for (size_t j = 1; j < NUM_RANKS; j++) {
			EXPECT_EQ(maybeEvicted->second[j], true);
		}
	}
}

/* filteraggregator tests */

// Tests that the filter evict function does nothing
TEST_F(FilterAggregatorTest, FilterEvict)
{
	auto message = std::string{"testing"};

	{ auto maybeEvicted = filterAggregator.evict();
		// expecting nothing evicted
		EXPECT_EQ(maybeEvicted == boost::none, true);
	}
}

// Tests that the filter update function does nothing
TEST_F(FilterAggregatorTest, FilterUpdate)
{
	auto message = std::string{"testing"};

	for (size_t i = 0; i < NUM_RANKS; i++) {
		// insert message into aggregator
		auto maybeEvicted = filterAggregator.update(message, i);
		// expecting nothing evicted
		EXPECT_EQ(maybeEvicted == boost::none, true);
	}
}

// Tests that the filter merge function provides correct access to bitset
TEST_F(FilterAggregatorTest, FilterMerge)
{
	auto message = std::string{"testing"};

	// fill group {0}
	{ auto maybeEvicted = filterAggregator.update(message, 0);
		// expecting nothing evicted
		EXPECT_EQ(maybeEvicted == boost::none, true);
	}

	// fill group {1 ... NUM_RANKS}
	rank_set_t firstMergeBitset{NUM_RANKS};
	for (size_t i = 1; i < NUM_RANKS; i++) {
		firstMergeBitset.set(i);
	}

	// fill group {0}
	rank_set_t secondMergeBitset{NUM_RANKS};
	secondMergeBitset.set(0);

	// perform merges
	filterAggregator.merge(message, firstMergeBitset);
	filterAggregator.merge(message, secondMergeBitset);

	// check merge
	for (auto&& objRanksetPair : filterAggregator) {
		// expecting evicted: message and full bitset
		EXPECT_EQ(objRanksetPair.first, message);

		// check bitset
		for (size_t j = 0; j < NUM_RANKS; j++) {
			EXPECT_EQ(objRanksetPair.second[j], true);
		}
	}
}
