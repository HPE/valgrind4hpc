#pragma once

#include "gtest/gtest.h"

#include "utils/Socket.hpp"

// The fixture for testing the Socket object
class SocketTest : public ::testing::Test
{
protected:
	Socket socket;

	SocketTest()
		: socket{}
	{}

	~SocketTest() override
	{}
};