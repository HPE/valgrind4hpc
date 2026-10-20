--[[

    Module valgrind4hpc

    <COPYRIGHT>
    UNPUBLISHED PROPRIETARY INFORMATION.
    ALL RIGHTS RESERVED.
    
]]--

-- local vars: define & assign --

-- template variables ----------------------------------------------------------
local INSTALL_ROOT       = "[@%PREFIX_PATH%@]"
local MOD_LEVEL          = "[@%MODULE_VERSION%@]"
--------------------------------------------------------------------------------

local NICKNAME  = "valgrind4hpc"
local PE_DIR    = INSTALL_ROOT .. "/" .. NICKNAME .. "/" .. MOD_LEVEL

 -- module release info variables
local REL_FILE            = PE_DIR .. "/release_notes.md"
local rel_info            = ""
if isFile(REL_FILE) then
    local f = io.open(REL_FILE, "r")
    local data = f:read("*all")
    f:close()
    if data ~= nil then rel_info = data end
end

 -- standered Lmod functions --

help ([[

The modulefile defines the system paths and
variables for the product valgrind4hpc.

]] .. rel_info .. "\n" .. [[

===================================================================
To re-display ]] .. tostring(myModuleName()) .. "/" .. MOD_LEVEL .. [[ release information,
type:    less ]] .. REL_FILE .. "\n" .. [[
===================================================================

]])

whatis("Loads valgrind4hpc.")

 -- environment modifications --

setenv        (    "VALGRIND4HPC_LEVEL",                MOD_LEVEL                      )
setenv        (    "VALGRIND4HPC_BASEDIR",              PE_DIR                         )
setenv        (    "PE_VALGRIND4HPC_MODULE_NAME",       myModuleName()                 )
setenv        (    "PE_VALGRIND4HPC_DIR",               PE_DIR                         )
setenv        (    "VALGRIND4HPC_INSTALL_DIR",          PE_DIR                         )

append_path   (    "PE_PRODUCT_LIST",                   "VALGRIND4HPC"                 )

prepend_path  (    "PATH",                              PE_DIR .. "/bin"               )
prepend_path  (    "MANPATH",                           PE_DIR .. "/share/man"         )

-- Load MRNet package dependency --
if (not isloaded("cray-mrnet")) then
    load("cray-mrnet")
end
