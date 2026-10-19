# cdst-test

Tools and libraries for facilitating push button functional testing of CDST products.

## Files and Directories

### `cdst_test/`

`cdst_test` is a python 3 (developed with python 3.6 in mind) library used by `test_tool.py` and `remote_test_tool.py` to facilitate automatic test setup and execution.

See `./cdst_test/README.md` for a more detailed breakdown.

### `test_tool.py`

The job of `test_tool.py` is to automatically set up a testing environment (by downloading avocado, checking that jobs can be run, etc) and run tests in a `tests.py` file in its working directory.

### `remote_test_tool.py`

The job of `remote_test_tool.py` is to remotely connect to a server, deliver `cdst_test`, and start a test server. After setup is complete, the responsibility of actually testing products is given to `test_tool.py` and `remote_test_tool.py` simply orchestrates communication and consumes results.

```
$ test_tool.py -p
```

### `tests/`

Unit tests for `cdst_test` library functions and a default test collection for `remote_test_tool.py` functions. To support a new product under cdst-test, it should have a similar `tests` directory. See `test_tool.py` usage below for more information on directory layout.

## `test_tool.py` usage

To run the test tool, make sure:
- `test_tool_config.yaml` is in your current working directory
- `tests.py` is in your current working directory

And then run:

```
$ ./test_tool.py
```

The contents of `test_tool_config.yaml` and `tests.py` vary by product and are not provided by the test tool. Instead, each cdst product supplies its own version of them and `test_tool.py` is a generic harness that hooks into them. The `tests/` directory in this repositoy has examples of `test_tool_config.yaml` and `tests.py`.

Running the test tool will:
- Check that your current environment is capable of building and launching MPI jobs
- Install avocado, the external test harness library we use, to your current working directory in a virtual environment
- Build test binaries (varies by product)
- Run the tests in `./tests.py`

Additional actions and options can be specified by suppliying arguments to `test_tool.py`. To see a full description of available arguments, run:

```
$ ./test_tool.py -h
```

### `test_tool.py` command line arguments

- `-t TEST`, `--test TEST`

    Run a single test. If this option isn't used, all tests are run. **TEST** should match the class name of an avocado test in `tests.py`. Can be used multiple times to run multiple tests.

- `-c LOCATION`, `--cp LOCATION`

    Copy test environment to another location. Useful if a tests rpm got installed in a location where you don't have write access, which is required to install avocado in a local virtual environment.

- `-s`, `--skip-build`

    Skip building tests and go straight into testing.

- `-f`, `--force`

    Force tests to run, even if a check fails.

- `-r`, `--remove`, `--clean`

    Remove local files that get created when `test_tool.py` is run.

- `-y FILE`, `--yaml FILE`

    Specify a yaml file to use instead of `test_tool_config.yaml`.

- `-e`, `--env`

    Dump environment info and exit.

- `-m FILTER`, `--mux-filter-only FILTER`

    Pass to avocado's `--mux-filter-only` argument.

- `-p`, `--print-default-config`

    Print a default `test_tool_config.yaml` file and exit.

## `remote_test_tool.py` usage

`remote_test_tool.py` is designed to set up testing environments appropriate for `test_tool.py` on remote machines, deliver `test_tool.py` to said machine, run tests, and report results.

To run `remote_test_tool.py`, you need to tell it where to run tests. More specifically, `remote_test_tool.py` needs a list of hostnames. You can generate this list of hostnames in a few different ways via command line arguments to `remote_test_tool.py`:

- `-o HOST`, `--on-host HOST`, e.g. "`-o horizon`", "`-o horizon -o pegasus`"

    Add **HOST** to the list of hostnames that `remote_test_tool.py` will run tests on. Can be used an arbitrary amount of times to select multiple hosts.

- `-O HOST'`, `--off-host HOST`, e.g. "`-O kay`", "`-O cfa6k -O pea2k`"

    The inverse of `-o`. Makes sure that after automatic hosts selection (see `-q` below), **HOST** is not in the final list.

- `-q QUALEXPR`, `--qualities QUALEXPR`, e.g. "`-q xc`", "`-q '(xc & slurm)'`"

    Select host "qualities" and have `remote_test_tool.py` query an internal database of hosts and select a list of hosts that match the "quality expression" **QUALEXPR**.

    Available qualities are things like system flavor (xc, apollo, shasta, etc) and system WLM (slurm, pals). For a full list of available qualities, run `./remote_test_tool.py -L`.

    A **QUALEXPR** can be built up by using set operations like union and intersection on a selection of qualities. For example, if you want to test on xc machines with the slurm WLM, pass `-q 'xc & slurm'`. If you want machines that are either xc or apollo and *don't* run pals, pass `-q '(xc | apollo) - pals'`. When passing a **QUALEXPR** containing spaces, make sure to surround it in quotes.

- `-l`, `--list-hosts`

    If this option is passed, `remote_test_tool.py` will run its automatic host list generation, taking into account `-o`, `-O`, and `-q`, print the generated list of hosts, and then exit.

After you decide where to run tests, `remote_test_tool.py`'s default options are enough to (attempt to) take over. By default, it will look for a local directory called `./tests` (which must contain `test_tool.py` and `test_tool_config.yaml`, see `test_tool.py` usage above), deliver it to the remote hosts, and remotely run the `test_tool.py` inside.

For example, to run the unit tests in this repository on `pegasus`, run:

```
$ ./remote_test_tool.py -o pegasus
```

`remote_test_tool.py` supports many command line options in order to customize the behavior. To see a full description of available arguments, run:

```
$ ./remote_test_tool.py -h
```

### `remote_test_tool.py` command line arguments

#### Connection arguments

- `-p PORT`, `--port PORT`

    On startup, `remote_test_tool.py` picks a random port to start its remote server on. If there are multiple machines being tested, the random port is used as a starting point and the chosen port is incremented for each machine.

    To explicitly choose this starting port instead of relying on a random choice, use `-p`.

- `-u USER`, `--user USER`

    Connect to the remote machines as **USER** instead of the local user running `remote_test_tool.py`.

- `-k PATH`, `--ssh-key PATH`

    Use the private ssh key at **PATH** to authenticate with remote machines instead of generating a single use key.

#### Auto host selection arguments

- `-o HOST`, `--on-host HOST`, e.g. "`-o horizon`", "`-o horizon -o pegasus`"

    Add **HOST** to the list of hostnames that `remote_test_tool.py` will run tests on. Can be used an arbitrary amount of times to select multiple hosts.

- `-O HOST'`, `--off-host HOST`, e.g. "`-O kay`", "`-O cfa6k -O pea2k`"

    The inverse of `-o`. Makes sure that after automatic hosts selection (see `-q` below), **HOST** is not in the final list.

- `-q QUALEXPR`, `--qualities QUALEXPR`, e.g. "`-q xc`", "`-q '(xc & slurm)'`"

    Select host "qualities" and have `remote_test_tool.py` query an internal database of hosts and select a list of hosts that match the "quality expression" **QUALEXPR**.

    Available qualities are things like system flavor (xc, apollo, shasta, etc) and system WLM (slurm, pals). For a full list of available qualities, run `./remote_test_tool.py -L`.

    A **QUALEXPR** can be built up by using set operations like union and intersection on a selection of qualities. For example, if you want to test on xc machines with the slurm WLM, pass `-q 'xc & slurm'`. If you want machines that are either xc or apollo and *don't* run pals, pass `-q '(xc | apollo) - pals'`. When passing a **QUALEXPR** containing spaces, make sure to surround it in quotes.

- `-l`, `--list-hosts`

    If this option is passed, `remote_test_tool.py` will run its automatic host list generation, taking into account `-o`, `-O`, and `-q`, print the generated list of hosts, and then exit.

- `-L`, `--list-qualities`

    List qualities available for use with `-q` and exit.

#### Test and product related arguments

- `-t PATH or PRODUCT:BRANCH`, `--tests PATH or PRODUCT:BRANCH`, e.g. `-t gdb4hpc:master`, `-t gdb4hpc:release-21.12`, `-t gdb4hpc:release-latest`

    Local **PATH** to directory containing `test_tool.py` and `tests.py`, or a **PRODUCT:BRANCH** string to download them from artifactory. **PRODUCT** should be the name of a CDST product (`e.g. atp, gdb4hpc`). Valid choices for **BRANCH** are `master`, `release-latest`, or `release-VERSION`, where **VERSION** is of the form XX.YY (e.g. 21.12). See `-I` for more info.

- `-i PRODUCT:BRANCH`, `--install PRODUCT:BRANCH`, e.g. `-t gdb4hpc:master`, `-t gdb4hpc:release-21.12`, `-t gdb4hpc:release-latest`

    Tell the test server to install **PRODUCT:BRANCH** from artifactory. **PRODUCT** should be the name of a CDST product (`e.g. atp, gdb4hpc`). Valid choices for **BRANCH** are `master`, `release-latest`, or `release-VERSION`, where **VERSION** is of the form XX.YY (e.g. 21.12). See `-I` for more info.

- `-b PRODUCT:BRANCH`, `--bundle PRODUCT:BRANCH`, e.g. `-b gdb4hpc:master`, `-b gdb4hpc:release-21.12`, `-b gdb4hpc:release-latest`

    Shorthand for passing `-t` and `-i` together with the same value. **PRODUCT** should be the name of a CDST product (`e.g. atp, gdb4hpc`). Valid choices for **BRANCH** are `master`, `release-latest`, or `release-VERSION`, where **VERSION** is of the form XX.YY (e.g. 21.12). See `-I` for more info.

- `I`, `--list-products`

    List products available for automatic install (see `-i`, `-t`, and `-b`) and exit.

- `-m MODULE`, `--module MODULE`, e.g. `-m gdb4hpc`, `-m gdb4hpc/4.10.3`, `-m gdb4hpc/latest`

    Load **MODULE** on the remote machine before testing. **MODULE** should be the name of a CDST product module with an optional version tag. Valid formats are `MODULE` (i.e. a product name no version tag, loads the default installed version), `MODULE/x.y.z`, where x.y.z is a numeric version, and `latest:MODULE` (loads latest available on the system).

- `s PATH`, `--module-use PATH`

    Run `module use PATH` on the remote machine before loading modules specified with `-m`.

#### Miscellaneous and debug arguments

These arguments aren't necessarily meant for normal use. They are useful primarily for debugging and development of `remote_test_tool.py`.

- `--server-port PORT`

    If specified, `remote_test_tool.py` will start in "server mode" and listen for a connection from its respective client on **PORT**. This is the "test server" mentioned in other places in this document.

- `--manual-server`

    Don't remotely start the testing server automatically. Assume that it has already been started on the remote machine and move straight to setting up a connection. Useful for manually running the test server for debugging.

- `--id-string IDSTRING`

    Each time `remote_test_tool.py` runs, it generates a unique string which it uses to name files and folders. If this option is specified, `remote_test_tool.py` will use the passed **IDSTRING** instead of the randomly generated string.

- `--clean-old`

    If specified, `remote_test_tool.py` will clean up the remote directory containing individual testing directories. It will delete any directories older than a certain internal number of days (see `./cdst_test/ssh.py:SshContext::cleanup_old_test_directories`). Use with caution!

- `--log-mode`

    If specified, the test tool will redirect all of its output to a log file.
