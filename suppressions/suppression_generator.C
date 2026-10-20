/******************************************************************************\
 * suppression_generator.C - Program to automatically generate suppression files
 *                           for Cray internal library calls.
 *
 * Copyright 2017,2020 Hewlett Packard Enterprise Development LP..
 *
 * Unpublished Proprietary Information.
 * This unpublished work is protected to trade secret, copyright and other laws.
 * Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
 * no part of this work or its content may be used, reproduced or disclosed
 * in any form.
 *
 ******************************************************************************/

#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include <getopt.h>

static struct option long_options[] = {
	{"func_file", required_argument, nullptr, 'f'},
	{"out_file", required_argument, nullptr, 'o'},
	{"help", no_argument, nullptr, 'h'},
	{nullptr, 0, nullptr, 0}
};

static const char * const valgrind_supp_str[] =
{
	"Value1", "Value2", "Value4", "Value8", "Value16",
	"Addr1", "Addr2", "Addr4", "Addr8", "Addr16",
	"Cond", "Jump", "Leak", "Free"
};

static const char * const valgrind_supp_param_str[] =
{
	"ioctl(generic)", "socketcall.sendto(msg)", "set_robust_list(head)"
};

static std::ifstream input_file;
static std::ofstream output_file;

static void
print_help( char * bin_name ) {
	std::cout << "Usage: " << bin_name << " <args>" << std::endl;
	std::cout << "Generate valgrind suppressions from a list of interface calls." << std::endl;
	std::cout << std::endl;
	std::cout << "\t-f, --func_file\tInput file containing functions to generate suppressions for. One function per line, no whitespace." << std::endl;
	std::cout << "\t-o, --out_file\tOutput file to write generated suppressions to. File will be truncated." << std::endl;
	std::cout << "\t-h, --help\tDisplay this text and exit." << std::endl;
	std::cout << std::endl;
	std::cout << "Example: " << bin_name << " -f func_file.in -o auto.supp" << std::endl;
}

int 
main( int argc, char *argv[] ) {
	input_file.exceptions( std::ifstream::failbit | std::ifstream::badbit );
	output_file.exceptions( std::ofstream::failbit | std::ofstream::badbit );
	// process the arguments
	int ch; int option_index;
	while ((ch = getopt_long(argc, argv, "f:o:h", long_options, &option_index)) != -1)
	{
		switch (ch)
		{
			case 'f':
				try {
					input_file.open( std::string(optarg), std::ifstream::in );
				} catch ( std::ifstream::failure e ) {
					std::cerr << "Could not open function file " << std::string(optarg) << " for reading." << std::endl;
					exit(1);
				}
				break;

			case 'o':
				try {
					output_file.open( std::string(optarg), std::ofstream::out | std::ofstream::trunc );
				} catch( std::ofstream::failure e ) {
					std::cerr << "Could not open output file " << std::string(optarg) << " for writing." << std::endl;
					exit(1);
				}
				break;

			case 'h':
				print_help( argv[0] );
				exit(0);

			default:
				print_help( argv[0] );
				exit(1);
		}
	}

	// Ensure user provided arguments
	if ( !input_file.is_open() || !output_file.is_open() ) {
		std::cerr << "Error: Must provide function file and output file arguments!" << std::endl;
		print_help( argv[0] );
		exit(1);
	}

	// process each line in the input file
	int suppcnt = 1;
	try {
		for ( std::string line; std::getline( input_file, line ); )
		{
			for (const char * const str : valgrind_supp_str)
			{
				output_file << "{"											<< std::endl;
				output_file << "        Cray autogen Supp " << suppcnt++	<< std::endl;
				output_file << "        Memcheck:" << str 					<< std::endl;
				output_file << "        ..." 								<< std::endl;
				output_file << "        fun:" << line 						<< std::endl;
				output_file << "}"											<< std::endl;
			}
			// Generate suppressions for each system call. Valgrind requires each syscall to be called out.
			for (const char * str : valgrind_supp_param_str)
			{
				output_file << "{"											<< std::endl;
				output_file << "        Cray autogen Supp " << suppcnt++	<< std::endl;
				output_file << "        Memcheck:Param"						<< std::endl;
				output_file << "        " << str							<< std::endl;
				output_file << "        ..." 								<< std::endl;
				output_file << "        fun:" << line 						<< std::endl;
				output_file << "}"											<< std::endl;
			}
		}
	} catch( ... ) {
		// Only a problem if input file isn't currently at eof...
		// FIXME: This is a hack.
		if ( !input_file.eof() ) {
			std::cerr << "Unhandled exception occured." << std::endl;
			throw;
		}
	}

	input_file.close();
	output_file.close();

	return 0;
}
