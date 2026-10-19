# cdst_test

`cdst_test` is a python 3 (developed with python 3.6 in mind) library used by `test_tool.py` and `remote_test_tool.py` to facilitate automatic test setup and execution.

## Files and Directories

### `data/`

Holds `.yaml` files used by the test tool as internal databases for host lookup and product lookup.

### `src/`

Holds `.c` MPI source used for automatically testing if a machine can build and run MPI apps.

### `scripts/`

Holds some useful scripts that could be more easily expressed in languages that aren't python. This is where the `.expect` scripts used for automatically logging in to servers via password are stored.

### `__init__.py`

Required by python to use this directory as a python module.

### `artifactory.py`

Functions for connecting to artifactory and downloading things.

### `config.py`

Functions for reading and acting upon the contents of a `.yaml` configuration file. See `README_config.md`.

### `config_default.py`

Functions for generating the default configuration settings for `test_tool.py`. See `README_config.md`.

### `config_nodes.py`

Functions and classes that make up the configuration tree used by `config.py`. See `README_config.md`.

### `env.py`

Names of environment variables that this library reads and responds to. See the contents of the file for descriptions of both internal and external variables.

### `files.py`

Functions used by the library to find the absolute path of the data directories.

### `job_environment.py`

Functions for detecting certain job environment edge cases and attempting to fix them.

### `log.py`

Custom log module tailored to the multi-threaded nature of `remote_test_tool.py` (But `test_tool.py` uses it too).

### `modules.py`

Wrapper that hooks into the installed `modules` python module.

### `remote_test_tool_startup.py`

Functions for parsing command line arguments, determining hosts, and providing examples of options for `remote_test_tool.py`. Due to the nature of `remote_test_tool.py` being both the client and the server (see `test_server.py`), `remote_test_tool_startup.py` needs to be included in this library, even if the remote server doesn't use it, so that there are no import problems.

### `remote_test_tool_ui.py`

Functions for displaying test results to a terminal or log file. Due to the nature of `remote_test_tool.py` being both the client and the server (see `test_server.py`), `remote_test_tool_startup.py` needs to be included in this library, even if the remote server doesn't use it, so that there are no import problems.

### `ssh.py`

Functions for remotely connecting to a machine over ssh and running tests.

### `test_server.py`

Main and functions for the test server. This file is invoked when `remote_test_tool.py` is started with the `--server-port` option. The server listens for commands from `remote_test_tool.py` and executes them with the code in `test_server_commands.py`.

### `test_server_commands.py`

Implementation of all commands the test server supports.

### `test_server_proto.py`

Protocol for sending commands back and forth between `remote_test_tool.py` and the test server.

### `textcheck.py`

Functions used by tests to match the output of a product to an expected output. See `README_textcheck.md`.

### `useful.py`

Useful helper functions for `test_tool.py` and `remote_test_tool.py`
