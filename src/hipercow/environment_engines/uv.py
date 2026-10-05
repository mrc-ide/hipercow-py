"""Create Python virtual environments using uv."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from uv import find_uv_bin

from hipercow.environment_engines.base import Platform
from hipercow.environment_engines.pip import Pip
from hipercow.root import Root
from hipercow.util import subprocess_run

_UV_SUBCOMMANDS = {"pip", "sync", "cache"}

_UV_PIP_SUBCOMMANDS = {
    "install",
    "uninstall",
    "sync",
    "list",
    "freeze",
    "show",
    "tree",
    "check",
}

# hipercow decides which interpreter is used and where the
# environment lives, so these must not be given by the user.
_UV_FORBIDDEN_ARGS = {"-p", "--python", "--system", "--prefix", "--target"}


class Uv(Pip):
    """Python virtual environments, created and installed by uv.

    We use [uv](https://docs.astral.sh/uv/) to create the virtual
    environment and install packages into it.  uv downloads a
    standalone build of Python, which we keep within the environment,
    so the Python version used by your tasks does not depend on what
    is installed on the cluster, and you can choose any version that
    uv can provide.  Any Python installed on the system is ignored.

    The `uv` executable comes from the `uv` package, which is
    installed alongside hipercow.  Set the environment variable
    `HIPERCOW_UV` to use a different copy.

    Once created, the environment is an ordinary virtual environment
    and tasks run in it exactly as they do for `Pip`.

    Attributes:
        python: The Python version requested, as given to `uv venv
            --python` (e.g., `3.12`).  If `None`, uv selects a version
            from `.python-version` or the `requires-python` field of
            `pyproject.toml` if present, otherwise the latest stable
            version.

    """

    def __init__(
        self,
        root: Root,
        name: str,
        platform: Platform | None = None,
        *,
        python: str | None = None,
    ):
        super().__init__(root, name, platform)
        self.python = python

    def path_uv(self) -> Path:
        """Compute path to uv's own files for this environment.

        This holds the environment's copy of Python (in `python/`) and
        uv's cache (in `cache/`) and is kept separately for each
        platform, alongside the environment itself.

        Returns:
            The path to the directory of uv files.

        """
        contents = self.root.path_environment_contents(self.name)
        return contents / f"uv-{self.platform.system}"

    def path_python(self) -> Path:
        """Compute path to the environment's copy of Python.

        Returns:
            The path to the Python executable.

        """
        if self.platform.system == "windows":
            return self.path_uv() / "python" / "python.exe"
        return self.path_uv() / "python" / "bin" / "python3"

    def create(self, **kwargs) -> None:
        """Create the virtual environment.

        First uv chooses and downloads Python into a temporary
        directory on this machine, by creating a throwaway environment
        there with

        ```
        uv venv <tmp>
        ```

        We copy that Python into the environment and then create the
        virtual environment at `path()` from the copy, with

        ```
        uv venv --python <copy> <path>
        ```

        We do this rather than have uv download Python straight onto
        the network share because, on Windows, uv links each minor
        version of Python to its latest patch version with a junction,
        and junctions cannot be created on network shares.

        Args:
            **kwargs (Any): Additional arguments to `subprocess_run`

        Returns:
            Nothing, called for side effects only.
        """
        uv = _uv()
        with tempfile.TemporaryDirectory() as tmp:
            env = self._uv_envvars_download(Path(tmp) / "python")
            probe = Path(tmp) / "venv"
            cmd = [uv, "venv", str(probe)]
            subprocess_run(cmd, check=True, env=env, **kwargs)
            exe = (
                "python.exe" if self.platform.system == "windows" else "python"
            )
            home = _base_prefix(probe / self._venv_bin_dir() / exe)
            path_python = self.path_uv() / "python"
            if path_python.exists():
                shutil.rmtree(path_python)
            shutil.copytree(home.resolve(), path_python, symlinks=True)
        python = str(self.path_python().absolute())
        cmd = [uv, "venv", "--python", python, str(self.path())]
        subprocess_run(cmd, check=True, env=self._uv_envvars(), **kwargs)

    def check_args(self, cmd: list[str] | None) -> list[str]:
        """Validate uv installation command.

        Checks if `cmd` is a valid command.  This may be a `pip`
        command (e.g., `pip install cowsay`), which is run as `uv pip`,
        or a `uv` command; one of `uv pip ...`, `uv sync ...` or `uv
        cache ...`.  The `pip` subcommand must be one supported by
        `uv pip`: `install`, `uninstall`, `sync`, `list`, `freeze`,
        `show`, `tree` or `check`.  You must not pass `--python` (or
        `-p`), `--system`, `--prefix` or `--target` as hipercow
        manages the location of the environment; choose the Python
        version when you create the environment.

        If `cmd` is `None` or the empty list, we try and guess a
        default command, based on files found in your project root.

        * if you have a `uv.lock` file, then we will run `uv sync
          --locked`

        * if you have a `pyproject.toml` file, then we will run
          `pip install .`

        * if you have a `requirements.txt`, then we will run `pip
          install -r requirements.txt`

        Args:
            cmd: The command to validate

        Returns:
            A validated list of arguments.
        """
        if not cmd:
            return self._auto()
        if cmd[0] == "pip":
            args = cmd
        elif cmd[0] == "uv":
            args = cmd[1:]
            if not args or args[0] not in _UV_SUBCOMMANDS:
                valid = ", ".join(f"'{x}'" for x in sorted(_UV_SUBCOMMANDS))
                msg = f"Expected second element of 'cmd' to be one of {valid}"
                raise Exception(msg)
        else:
            msg = "Expected first element of 'cmd' to be 'pip' or 'uv'"
            raise Exception(msg)
        if args[0] == "pip" and (
            len(args) == 1 or args[1] not in _UV_PIP_SUBCOMMANDS
        ):
            valid = ", ".join(f"'{x}'" for x in sorted(_UV_PIP_SUBCOMMANDS))
            msg = f"Expected 'pip' to be followed by one of {valid}"
            raise Exception(msg)
        for arg in args[1:]:
            # split to catch the '--python=3.12' form too
            if arg.split("=")[0] in _UV_FORBIDDEN_ARGS:
                msg = (
                    f"Don't use '{arg}' when provisioning; hipercow "
                    "manages the location of the environment (set the "
                    "Python version with 'hipercow environment new "
                    "--python')"
                )
                raise Exception(msg)
        return cmd

    def provision(self, cmd: list[str], **kwargs) -> None:
        """Provision a virtual environment using uv.

        Args:
            cmd: The command to run, as validated by `check_args`

            **kwargs (Any): Additional arguments to `subprocess_run`

        Returns: Nothing, called for its side effect only.

        """
        args = cmd[1:] if cmd[0] == "uv" else cmd
        if args[0] == "pip":
            # 'uv pip' needs telling which environment to act on;
            # 'uv sync' finds it through UV_PROJECT_ENVIRONMENT.
            args = ["pip", args[1], "--python", str(self.path()), *args[2:]]
        cmd_uv = [_uv(), *args]
        subprocess_run(cmd_uv, check=True, env=self._uv_envvars(), **kwargs)

    def _uv_envvars(self) -> dict[str, str]:
        # Keeping the cache within the environment means that every
        # node that can see the root can see it, and that deleting
        # the environment removes it.  Every command uses the
        # environment's copy of Python, so uv never downloads another
        # (into your home directory) or uses one from the system.
        return {
            "UV_CACHE_DIR": str(self.path_uv() / "cache"),
            "UV_PYTHON": str(self.path_python().absolute()),
            "UV_PYTHON_DOWNLOADS": "never",
            "UV_PROJECT_ENVIRONMENT": str(self.path()),
        }

    def _uv_envvars_download(self, path: Path) -> dict[str, str]:
        # Used while creating the environment, so that uv chooses the
        # version of Python (from 'python', '.python-version' or
        # 'requires-python') and downloads it into 'path'.
        env = {
            "UV_CACHE_DIR": str(self.path_uv() / "cache"),
            "UV_PYTHON_INSTALL_DIR": str(path),
            "UV_MANAGED_PYTHON": "1",
        }
        if self.python:
            env["UV_PYTHON"] = self.python
        return env

    def _auto(self) -> list[str]:
        if Path("uv.lock").exists():
            return ["uv", "sync", "--locked"]
        if Path("pyproject.toml").exists():
            return ["pip", "install", "."]
        if Path("requirements.txt").exists():
            return ["pip", "install", "-r", "requirements.txt"]
        msg = "Can't determine install command"
        raise Exception(msg)


def _base_prefix(python: Path) -> Path:
    code = "import sys; print(sys.base_prefix)"
    res = subprocess.run(
        [str(python), "-c", code], check=True, capture_output=True, text=True
    )
    return Path(res.stdout.strip())


def _uv() -> str:
    path = os.environ.get("HIPERCOW_UV")
    if path:
        if not Path(path).exists():
            msg = f"'HIPERCOW_UV' is set to '{path}', but this does not exist"
            raise Exception(msg)
        return path
    return find_uv_bin()
