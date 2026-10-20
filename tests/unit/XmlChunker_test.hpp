#pragma once

#include "gtest/gtest.h"

#include "utils/XmlChunker.hpp"

// The fixture for testing the XML chunking mechanism
class XmlChunkerTest : public ::testing::Test
{
	protected:
		std::stringstream xmlStream;
		XmlChunker chunker;

		XmlChunkerTest()
			: xmlStream{}
			, chunker{xmlStream}
		{}

		~XmlChunkerTest() override
		{}
};
