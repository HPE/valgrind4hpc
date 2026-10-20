#include <string>

#include "XmlChunker_test.hpp"

// Tests that an empty stream will yield no tags or blocks
TEST_F(XmlChunkerTest, None)
{
	EXPECT_EQ(chunker.readTag(), "");
	EXPECT_EQ(chunker.readBlock(), "");
}

TEST_F(XmlChunkerTest, OneTag)
{
	auto const tagContents = std::string{"?xml ?"};

	xmlStream << "<" << tagContents << ">" << std::endl;

	EXPECT_EQ(chunker.readTag(), tagContents);
	EXPECT_EQ(chunker.readTag(), "");
}

TEST_F(XmlChunkerTest, OneBlock)
{
	auto const blockContents = std::string{"<block>content</block>"};

	xmlStream << blockContents << std::endl;

	EXPECT_EQ(chunker.readBlock(), blockContents);
	EXPECT_EQ(chunker.readBlock(), "");
}

TEST_F(XmlChunkerTest, PartialBlock)
{
	auto const blockPart1 = std::string{"<block>content</block>"};
	auto const blockPart2 = std::string{"<partial>content"};

	xmlStream << blockPart1 << blockPart2 << std::endl;

	EXPECT_EQ(chunker.readBlock(), blockPart1);
	EXPECT_EQ(chunker.readBlock(), "");
}

TEST_F(XmlChunkerTest, TwoBlocks)
{
	auto const block1 = std::string{"<block1>content</block1>"};
	auto const block2 = std::string{"<block2>content</block2>"};

	xmlStream << block1 << block2 << std::endl;

	EXPECT_EQ(chunker.readBlock(), block1);
	EXPECT_EQ(chunker.readBlock(), block2);
	EXPECT_EQ(chunker.readBlock(), "");
}
