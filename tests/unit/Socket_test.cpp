#include <string>
#include <future>
#include <unordered_set>

#include "Socket_test.hpp"

#include "utils/ExecvpOutput.hpp"

static std::string
readSocket(Socket& socket)
{
	auto acceptBuf = FdBuf{socket.accept()};
	std::istream acceptStream{&acceptBuf};

	std::string result;
	std::string line;
	while (std::getline(acceptStream, line)) {
		result += line;
	}

	return result;
}

static void
sendString(std::string const& message, std::string const& address, std::string const& port)
{
	auto const netcatCommand = std::string{"echo " + message + " | netcat " + address + " " + port};
	char const* const netcatArgv[] = { "/bin/sh", "-c", netcatCommand.c_str(), nullptr };
	ExecvpOutput netcatOutput{"sh", (char* const*)netcatArgv};
	if (netcatOutput.getExitStatus()) {
		throw std::runtime_error{"netcat failed"};
	}
}

// testing constructor / destructor
TEST_F(SocketTest, None)
{}

// testing single accept instance
TEST_F(SocketTest, SingleAccept)
{
	auto stringFuture = std::async(std::launch::async, readSocket, std::ref(socket));

	auto const message = std::to_string(getpid());
	sendString(message, socket.getAddress(), socket.getPort());

	EXPECT_EQ(stringFuture.get(), message);
}
