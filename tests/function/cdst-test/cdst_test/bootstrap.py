#!/usr/bin/env python3

"""Example: bootstrap into a self-managed venv before running the real program.

On first run this creates a venv, installs requirements into it, and re-executes
the process with the venv's interpreter. On later runs it reuses the existing venv.
"""

import os
import subprocess
import sys
import venv
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV_DIR = HERE / ".venv"
REQUIREMENTS = HERE / "requirements.txt"

# Set in the child so a failed//partial bootstrap can't cause an exec loop.
_REEXEC_GUARD = "MYAPP_VENV_BOOTSTRAPPED"

def venv_python(venv_dir: Path) -> Path:
    return venv_dir / "bin" / "python"

def in_venv(venv_dir: Path) -> bool:
    """True if the current interpreter is the one inside venv_dir."""
    return Path(sys.prefix).resolve() == venv_dir.resolve()

def create_venv(venv_dir: Path) -> None:
    builder = venv.EnvBuilder(with_pip=True, clear=False, symlinks=(os.name != "nt"))
    builder.create(venv_dir)


def install_requirements(python: Path, requirements: Path) -> None:
    if not requirements.is_file():
        return
    subprocess.run(
        [str(python), "-m", "pip", "install", "--disable-pip-version-check",
         "-r", str(requirements)],
        check=True,
    )

def bootstrap() -> bool:
    """Return normally only when running inside the venv; otherwise re-exec."""
    print("in bootstrap")
    if in_venv(VENV_DIR):
        return True

    if os.environ.get(_REEXEC_GUARD):
        return False

    python = venv_python(VENV_DIR)
    fresh = not python.is_file()
    if fresh:
        # Build into a temp dir and rename so an interrupted run leaves no half-built venv.
        staging = VENV_DIR.with_name(VENV_DIR.name + ".tmp")
        if staging.exists():
            import shutil

            shutil.rmtree(staging)
        create_venv(staging)
        install_requirements(venv_python(staging), REQUIREMENTS)
        staging.rename(VENV_DIR)

    env = dict(os.environ)
    env[_REEXEC_GUARD] = "1"
    env["VIRTUAL_ENV"] = str(VENV_DIR)
    env["PATH"] = str(python.parent) + os.pathsep + env.get("PATH", "")
    # A stale PYTHONHOME would override the venv's prefix.
    env.pop("PYTHONHOME", None)

    os.execve(str(python), [str(python), sys.argv[0], *sys.argv[1:]], env)

if __name__ == "__main__":
    exit(0 if bootstrap() else -1)
