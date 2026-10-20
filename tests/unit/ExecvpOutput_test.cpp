#include <string>

#include "gtest/gtest.h"

#include "utils/ExecvpOutput.hpp"

TEST(ExecvpOutputTest, Echo)
{
	auto const message = std::to_string(getpid());
	char const* const echoArgv[] = { "echo", message.c_str(), nullptr };

	ExecvpOutput echoOutput{"echo", (char* const*)echoArgv};

	EXPECT_EQ(echoOutput.optional_getline(), boost::optional<std::string>{message});
}
