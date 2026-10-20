#pragma once

#include "gtest/gtest.h"

#include "valgrind4hpc_aggregator.h"

/* aggregator test fixtures */

static constexpr auto NUM_RANKS = size_t{4};

// The fixture for testing a full aggregator
class FullAggregatorTest : public ::testing::Test
{
	protected:
		FullAggregator<std::string> fullAggregator;

		FullAggregatorTest()
			: fullAggregator{NUM_RANKS}
		{}

		~FullAggregatorTest() override
		{}
};

// The fixture for testing a group aggregator
class GroupAggregatorTest : public ::testing::Test
{
	private:
		static rank_set_t make_firstGroup()
		{
			rank_set_t result{NUM_RANKS};
			result.set(0);
			return result;
		}

		static rank_set_t make_secondGroup()
		{
			rank_set_t result{NUM_RANKS};
			for (size_t i = 1; i < NUM_RANKS; i++) {
				result.set(i);
			}
			return result;
		}

	protected:
		GroupAggregator<std::string> firstGroupAggregator, secondGroupAggregator;

		GroupAggregatorTest()
			: firstGroupAggregator{make_firstGroup()}
			, secondGroupAggregator{make_secondGroup()}
		{}

		~GroupAggregatorTest() override
		{}
};

// The fixture for testing a filter aggregator
class FilterAggregatorTest : public ::testing::Test
{
	protected:
		FilterAggregator<std::string> filterAggregator;

		FilterAggregatorTest()
			: filterAggregator{}
		{}

		~FilterAggregatorTest() override
		{}
};
