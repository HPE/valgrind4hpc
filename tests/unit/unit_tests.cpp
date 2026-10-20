#include "valgrind4hpc_aggregator_test.hpp"
#include "MsgQueue_test.hpp"
#include "TSQueue_test.hpp"

int main(int argc, char **argv) {
	::testing::InitGoogleTest(&argc, argv);
	return RUN_ALL_TESTS();
}
