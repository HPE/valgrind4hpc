# `config.py`, `config_nodes.py`, and `config_default.py`

## Model

`remote_test_tool.py` and `test_tool.py` read from `.yaml` files at runtime for configuration. This configuration describes things like how many ranks to use in job launches, which environment variables need to be set, and which modules need to be loaded.

The process to setup a test environment can vary from machine to machine enough that there is no valid setup for every machine. Module names can change, or `LD_LIBRARY_PATH` might need to be manually modified, for example. For this reason the configuration for `remote_test_tool.py` and `test_tool.py` has a notion of **global defaults**, **product defaults**, and **host specific overrides**.

**Global defaults** are defined in code in `config_default.py` and are the baseline values used everywhere. You can see these defaults by running `test_tool.py -p`.

**Product defaults** are loaded from an individual product's `test_tool_config.yaml` file and overwrite any global defaults.

**Host specific overrides** are also loaded from an individual product's `test_tool_config.yaml` file (see below) and overwrite anything loaded before.

For example, the **global default** value for number for jobs to run in parallel for a given collection of tests might be a conservative value like `1`. This is the value used for *all products* unless otherwise stated in an individual product's `test_tool_config.yaml`. In a set of tests optimized for parallel execution, it might be set to something like `4` as a **product default**. However, even that is conservative, as it is again meant as a default value that will apply to all machines that run the set of tests. Some machines are more powerful and could support a different value like `16`. The individual product's `test_tool_config.yaml` has a dedicated section for such machines, the **host specific override (see below).

Thus, the model for loading runtime configuration for the test tools is as follows:

1. Load **global default** configuration
2. Load local `test_tool_config.yaml` file, the **product defaults**, overwriting some or all of the defaults
3. Check the `test_tool_config.yaml` file for any **host specific overrides** (see below) and apply them on top of the values loaded in step 2

## Schema

The configuration schema changes often. Often enough that documenting the schema in a static text document was consistently outdated. This was the motivation for defining the schema in code. The schema is defined in `config_default.py`. The schema is a tree of "configuration nodes", matching the tree-like structure of a `.yaml` file. The nodes are defined in `config_nodes.py`, but knowledge of the nodes' implementation isn't needed to write configuration files.

To see the exact schema that your version of `test_tool.py` is using and the default values, run `test_tool.py -p`. The output is in `.yaml` format and could be dropped right into `test_tool_config.yaml`.

The output of `test_tool.py -p` includes comments on what each option does. Additionally, there is an example `test_tool_config.yaml` file in the `/tests/` directory of this repository.

## Host Specific Overrides

To use host specific overrides, include an additional section at the bottom of `test_tool_config.yaml`. Start the section with the name of the hostname of the machine that it should apply to, and then define any overrides as children of the hostname node as if it were a normal configuration file.

For example, a `test_tool_config.yaml` that looks like this:

```
launch:
  prepend-env-vars: {} # prepend env vars before launching jobs

meta:
  avocado-version: "82.0" # version of avocado and avocado plugins to install

# system specific overrides
pea2k:
  launch:
    prepend-env-vars:
      LD_LIBRARY_PATH: /opt/cray/pe/pals/default/lib

horizon:
  meta:
    avocado-version: latest
```

When this file is read on `pea2k`, the extra `prepend-env-vars` option is applied and `/opt/cray/pe/pals/default/lib` is prepended to `LD_LIBRARY_PATH`. This only happens on `pea2k`.

Similarly, when the file is read on `horizon`, the `avocado-version` option kicks in and overrides the product default of `82.0` with `latest`. This only happens on `horizon`
