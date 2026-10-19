# Copyright 2021 Hewlett Packard Enterprise Development LP
#
# Config nodes for use in the config module

import os, re, subprocess
import multiprocessing

from . import modules, log
from . useful import successful_launch

class Node():
    # Base Node interface. The idea is that a tree of config nodes is constructed
    # describing test tool config. Each leaf node should impliment the apply/get
    # method to either do some config action or return data, respectively. The
    # nodes are "applied" by calling apply/get and passing a path to the leaf node.

    # name is the name of the node as it appears in a config file.
    # comment will show up as a yaml comment when generate_yaml is called.
    def __init__(self, name: str, comment = None):
        self.name = name
        self.children = {}
        self.comment = comment

    # Generate human readable, yet machine parsable yaml describing this node
    # and its subtree. The indent argument should not be specified manually.
    def generate_yaml(self, indent = 0) -> str:
        ind = " " * indent
        comment = f"# {self.comment}" if self.comment else ""

        y = f"{ind}{comment}\n" + f"{ind}{self.name}:\n"

        for name, node in self.children.items():
            y += node.generate_yaml(indent+2)

        return y

    def add_child(self, node) -> bool:
        if node.name in self.children:
            log.warn("name already exists")
            return False
        else:
            self.children[node.name] = node
            return True

    def add_children(self, nodes: list) -> bool:
        for n in nodes:
            if not self.add_child(n):
                return False
        return True

    # Search the subtree for a leaf node matching path. Path should resemble a
    # linux directory path, e.g. "test/modules", with the exception that there
    # should never be a leading slash.
    # TODO: fix to handle leading slash.
    def apply(self, path: str):
        if path == "":
            return self

        exploded = path.split("/")
        nxt = exploded[0]
        if nxt in self.children:
            return self.children[nxt].apply("/".join(exploded[1:]))
        else:
            log.error(f"Never found {path} in tree")
            return None

    # Alias for apply. More readable when "apply" simply returns data.
    def get(self, path: str):
        return self.apply(path)

    # Used to apply system specific overrides. Take a patch and if it matches
    # any subtrees, update the subtrees to include the patch.
    def patch_from_dict(self, patch : dict):
        for key, value in patch.items():
            if isinstance(value, dict) and key in self.children:
                self.children[key].patch_from_dict(patch[key])
            elif key in self.children:
                self.children[key].set(value)

class YamlRoot(Node):
    # Special case of a generic node that outputs yaml headers

    def __init__(self):
        super().__init__("root", comment=None)

    def generate_yaml(self, indent = 0):
        y = "---\n"

        for name, node in self.children.items():
            y += "\n" + node.generate_yaml(0)

        y += "\n# add system specific overrides here"

        return y

class KeyValue(Node):
    # A simple key/value store

    def __init__(self, key: str, value, comment = None):
        super().__init__(key, comment)
        self.value = value

    def apply(self, path: str):
        return self.value

    def set(self, value):
        self.value = value

    def generate_yaml(self, indent = 0):
        ind = " " * indent
        comment = f"# {self.comment}" if self.comment else ""
        value = self.value

        if isinstance(value, bool):
            value = "yes" if value else "no"
        elif isinstance(value, str):
            value = "\"" + value + "\""

        return f"{ind}{self.name}: {value} {comment}\n"

class Dict(Node):
    # Similar to key/value, but multiple keys/values can be used

    def __init__(self, key: str, map = {}, comment = None):
        super().__init__(key)
        self.map = map.copy()
        self.comment = comment

    def apply(self, path: str):
        if path == "":
            return self.map
        elif path in self.map:
            return self.map[path]
        else:
            log.error(f"Never found {path} in {self.name}")
            return None

    def patch_from_dict(self, patch : dict):
        for k, v in patch.items():
            if isinstance(v, dict):
                # topatch.get(k, {}) will return an empty dict if nothing exists for
                # that key, but None is not nothing, and None is also bad, so we turn
                # that into an empty dict too
                next_topatch = self.map.get(k, {}) if self.map.get(k, {}) is not None else {}
                self.map[k] = self.patch_from_dict(next_topatch, v)
            else:
                self.map[k] = v

    def generate_yaml(self, indent = 0):
        ind = " " * indent
        comment = f"# {self.comment}" if self.comment else ""
        short = "{} " if len(self.map) == 0 else ""

        y = f"{ind}{comment}\n" + f"{ind}{self.name}: {short}\n"

        for key, value in self.map.items():
            y += f"{ind}  {key}: \"{value}\"\n"

        # for name, node in self.children.items():
        #     y += node.generate_yaml(indent+2)

        return y

class List(Node):
    # A simple data list

    def __init__(self, name: str, the_list = [], comment=None):
        super().__init__(name, comment)
        self.list = the_list.copy()

    def apply(self, path: str):
        return self.list

    def set(self, l):
        self.list = l if l is not None else []

    def generate_yaml(self, indent = 0):
        ind = " " * indent
        comment = f"# {self.comment}" if self.comment else ""
        short = "[] " if len(self.list) == 0 else ""

        y = f"{ind}{comment}\n" + f"{ind}{self.name}: {short}\n"

        for i in self.list:
            y += f"{ind}- {i}\n"

        # for _, node in self.children.items():
        #     y += node.generate_yaml(indent+2)

        return y

class NodeList(Node):
    # Instead of a list of data, this node expects to have an arbitrary amount
    # of children matching the specified type.

    def __init__(self, name: str, child_type, comment=None):
        super().__init__(name, comment=comment)
        self.child_type = child_type

    def patch_from_dict(self, patch : dict):
        for key, value in patch.items():
            if isinstance(value, dict) and key in self.children:
                self.children[key].patch_from_dict(patch[key])
            elif key in self.children:
                self.children[key].set(value)
            else:
                self.add_child(node_from_dict(self.child_type, {key: value}))

    def apply(self, path: str):
        for _, node in self.children.items():
            if not node.apply(path):
                return False
        return True

class LoadModules(List):
    # Loads a list of modules. If optional is specified, failing to load a
    # certain module isn't fatal.

    def __init__(self, name: str = "modules", modules = [], optional=False):
        comment = "load these modules"
        self.optional = optional
        if self.optional:
            name = "optional-" + name
            comment = "try to load these modules, but failure isn't fatal"
        super().__init__(name, modules, comment)

    def apply(self, path: str):
        for mod in self.list or []:
            if "/" in mod:
                log.debug(f"Specific version module {mod} requested")
                # require a specific version
                # unload if another version is loaded
                loaded = modules.list(mod[:mod.find('/')])
                for loaded_mod in loaded:
                    if not modules.invoke_successfully("unload", loaded_mod):
                        log.error(f"Failed to unload {loaded_mod}")
                        return False

                log.info(f"Loading {mod}...")
                if not modules.invoke_successfully("load", mod):
                    if self.optional:
                        log.warn(f"Failed to load {mod}. Restoring old modules...")
                        successfully_restored = True
                        for loaded_mod in loaded:
                            log.warn(f"{loaded_mod}...")
                            if not modules.invoke_successfully("load", loaded_mod):
                                log.error(f"Failed to re-load {mod}.")
                                successfully_restored = False
                        if not successfully_restored:
                            return False
                        # otherwise continue outer loop
                    else:
                        log.error(f"Failed to load {mod}.")
                        return False
            else:
                # load if not already present
                loaded = modules.list(mod)
                if len(loaded) == 0:
                    # not present
                    log.info(f"Loading {mod}...")
                    if not modules.invoke_successfully("load", mod):
                        if self.optional:
                            log.warn(f"Failed to load optional module {mod}.")
                        else:
                            log.error(f"Failed to load {mod}.")
                            return False
                else:
                    log.warn(f"Module requirement \"{mod}\" already met by {loaded}, skipping")
        return True

class UnloadModules(List):
    # Unloads a list of modules

    def __init__(self, name: str = "unload-modules", modules=[]):
        super().__init__(name, modules, "unload these modules")

    def apply(self, path: str):
        for module in self.list:
            success = modules.invoke_successfully("unload", module)
            if not success:
                log.error(f"Failed to unload module \"{module}\"")
                return False
        return True

class EnvVarsPresent(List):
    # Ensure environment variables are present

    def __init__(self, name: str = "env-vars-present", vars = []):
        super().__init__(name, vars)
        self.comment = "ensure these environment variables are present"

    def apply(self, module: str):
        for evar in self.list:
            if not os.getenv(evar):
                log.error(f"Missing environment variable: {evar}")
                return False
        return True

class SetEnvVars(Dict):
    # Sets and overwrites environment variables

    def __init__(self, key: str = "environment", env={}):
        super().__init__(key, env, "overwrite environment variables")

    def apply(self, path: str):
        for var, value in self.map.items():
            value = str(value)

            # support looking up environment variables denoted by ${ABC}
            evars = re.findall(r"\$\{.*?\}", value)
            for v in evars:
                value = value.replace(v, os.environ[v[2:-1]])

            log.debug("Setting %s to %s." % (value, var))

            os.environ[var] = value

            log.warn("$%s is now \"%s\"" % (var, os.environ[var]))
        return True

class PrependEnvVars(Dict):
    # Prepends to existing environment variables PATH style (separated by a colon),
    # or simply sets them if they don't exist

    def __init__(self, key: str = "prepend-env-vars", env={}):
        super().__init__(key, env, "prepend environment variables")

    def apply(self, path: str):
        for var, value in self.map.items():
            value = str(value)

            # support looking up environment variables denoted by ${ABC}
            evars = re.findall(r"\$\{.*?\}", value)
            for v in evars:
                env_var = os.getenv(v[2:-1])
                if env_var is None:
                    log.error(f"Tried to use value of ${v[2:-1]} in config section \"{self.name}\", but the envrionment variable is not set.")
                    return False
                value = value.replace(v, env_var)

            log.debug("Prepending %s to %s." % (value, var))

            if var in os.environ and os.environ[var] != "":
                os.environ[var] = value + ":" + os.environ[var]
            else:
                os.environ[var] = value

            log.warn("$%s is now \"%s\"" % (var, os.environ[var]))
        return True

class PkgConfig(List):
    # Ensure that a certain package is visible to pkg-config. Takes no action
    # to load anything, only checks availability.

    def __init__(self, name: str = "pkg-config", list=[]):
        super().__init__(name, list, "ensure pkg-config can find these packages")

    def apply(self, path: str):
        for pkg in self.list:
            log.debug("Checking for package: " + pkg + "... ")
            result = subprocess.run(["pkg-config", "--exists", pkg]).returncode == 0
            if not result:
                log.error(f"Couldn't find pkg-config for {pkg}, check PKG_CONFIG_PATH")
                return False
        return True

class MakeTarget(Node):
    # Builds binaries via a makefile.

    def __init__(self, name: str = "all", always_rebuild = False, j = 1, load_modules = [], optional_load_modules = [], unload_modules = [], dir : str = ".", makefilename : str = "", can_fail = False):
        super().__init__(name, comment=f"make {name}")
        self.add_child(KeyValue("j", j, "build this many tests in parallel (make -j)"))
        self.add_child(KeyValue("always-rebuild", always_rebuild, "make clean and rebuild each time"))
        self.add_child(LoadModules(modules=load_modules))
        self.add_child(LoadModules(modules=optional_load_modules, optional=True))
        self.add_child(UnloadModules(modules=unload_modules))
        self.add_child(KeyValue("directory", dir, "run make in this directory"))
        self.add_child(KeyValue("file", makefilename, "use this makefile (make -f <file>)"))
        self.add_child(KeyValue("can-fail", can_fail, "continue with tests even if build fails"))

    def apply(self, path: str):
        def make(self, outq):
            log.info("Building " + self.name)

            if not self.apply("modules"):
                outq.put([False])
                return

            if not self.apply("optional-modules"):
                outq.put([False])
                return

            if not self.apply("unload-modules"):
                outq.put([False])
                return

            launch = ["make", self.name, "-C", self.get("directory"), "-j", str(self.get("j"))]

            if self.get("can-fail"):
                launch += ["-k"]

            if self.get("file"):
                launch += ["-f", self.get("file")]

            if self.get("always-rebuild") == True:
                launch += ["-B"]

            log.debug(f"launch: {launch}")
            if not successful_launch(launch):
                log.error("Failed to make " + self.name)
                outq.put([False])
                return

            outq.put([True])
            return

        if path == "":
            # Do make in sub process so module loads don't affect global environment
            outq = multiprocessing.Queue()
            p = multiprocessing.Process(target=make, args=(self, outq))
            p.start()
            p.join(60)
            if p.exitcode == None:
                # timed out
                log.error("make subprocess timed out")
                return False
            else:
                return outq.get()[0] | self.get("can-fail")
        else:
            return super().apply(path)

# Try to intelligently create a node from pure data. Used during patching.
def node_from_dict(type, data : dict):
    if type == MakeTarget:
        # not very smart... assuming the best for now
        if len(data.keys()) != 1:
            log.warn("tried to make a make target node from a dictionary with multiple keys")
        elif len(data.keys()) < 1:
            log.error("tried to make a make target node from a dictionary with no keys")
            return None
        name = next(iter(data))
        the_rest = data[name]
        j = the_rest["j"] if "j" in the_rest else 1
        always_rebuild = the_rest["always-rebuild"] if "always-rebuild" in the_rest else False
        load_modules = the_rest["modules"] if "modules" in the_rest else []
        optional_modules = the_rest["optional-modules"] if "optional-modules" in the_rest else []
        unload_modules = the_rest["unload-modules"] if "unload-modules" in the_rest else []
        dir = the_rest["directory"] if "directory" in the_rest else "."
        makefilename = the_rest["file"] if "file" in the_rest else ""
        can_fail = the_rest["can-fail"] if "can-fail" in the_rest else False
        return MakeTarget(
            name=name,
            always_rebuild=always_rebuild,
            j=j,
            load_modules=load_modules,
            optional_load_modules=optional_modules,
            unload_modules=unload_modules,
            dir=dir,
            makefilename=makefilename,
            can_fail=can_fail
        )
    else:
        log.error(f"node_from_dict unimplemented for {type}")
        return None
