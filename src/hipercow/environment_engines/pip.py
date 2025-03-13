"""Create Python virtual environments using pip."""

import os
import subprocess
from pathlib import Path

from hipercow.environment_engines.base import EnvironmentEngine, Platform
from hipercow.root import Root
from hipercow.util import subprocess_run, transient_envvars


class Pip(EnvironmentEngine):
    """Python virtual environments, installed by pip."""

    def __init__(self, root: Root, name: str, platform: Platform | None = None):
        super().__init__(root, name, platform)

    def path(self) -> Path:
        return super().path() / f"venv-{self.platform.system}"

    def create(self, **kwargs) -> None:
        """Create the virtual environment.

        Calls

        ```
        python -m venv <path>
        ```

        with the result of `path()`.

        Args:
            **kwargs (Any): Additional arguments to `subprocess_run`

        Returns:
            Nothing, called for side effects only.
        """
        cmd = ["python", "-m", "venv", str(self.path())]
        subprocess_run(cmd, check=True, **kwargs)

    def check_args(self, cmd: list[str] | None) -> list[str]:
        """Validate pip installation command.

        Checks if `cmd` is a valid `pip` command.

        If `cmd` is `None` or the empty list, we try and guess a
        default command, based on files found in your project root.

        * if you have a `pyproject.toml` file, then we will try and
          run `pip install --verbose .`

        * if you have a `requirements.txt`, then we will try and run
          `pip install --verbose -r requirements.txt`

        (In both cases these are returned as a list of arguments.)

        If there are other reasonable conventions that we might
        follow, please let us know.

        Args:
            cmd: The command to validate

        Returns:
            A validated list of arguments.
        """
        if not cmd:
            return self._auto()
        if cmd[0] != "pip":
            msg = "Expected first element of 'cmd' to be 'pip'"
            raise Exception(msg)
        return cmd

    def provision(self, cmd: list[str], **kwargs) -> None:
        """Provision a virtual environment using pip.

        Args:
            cmd: The command to run

            **kwargs (Any): Additional arguments to `Pip.run`

        Returns: Nothing, called for its side effect only.

        """
        self.run(cmd, check=True, **kwargs)

    def run(
        self,
        cmd: list[str],
        *,
        env: dict[str, str] | None = None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        """Run a command within the pip virtual environment.

        Args:
            cmd: The command to run

            env: Environment variables, passed into `subprocess_run`.
                We will add additional environment variables to
                control the virtual environment activation.  Note that
                `PATH` cannot be safely set through `env` yet,
                because we have to modify that to activate the virtual
                environment, and because `subprocess.Popen` requires
                the `PATH` to be set **before** finding the program to
                call on Windows.  We may improve this in future.

            **kwargs (Any): Keyword arguments to `subprocess_run`.

        Returns: Details about the process, if `check=True` is not
           present in `kwargs`
        """
        # If the user sets a PATH, within 'env' then we will clobber
        # that when we add our envvars to the dictionary.  Later we
        # can inspect 'env' for PATH and join them together, but it's
        # not obvious what the priority should really be.
        #
        # There's another subtlety about setting PATH; see the See the
        # Warning in
        # https://docs.python.org/3/library/subprocess.html#popen-constructor
        #
        # > For Windows, ... env cannot override the PATH environment
        # > variable. Using a full path avoids all of these
        # > variations.
        #
        # The other way of doing this would be shutil.which and
        # updating the command, but that feels worse because it
        # requires that the first line of the cmd is definitely the
        # program under executation (probably reasonable) and it will
        # require logic around only doing that if a relative path is
        # given, etc.
        env = (env or {}) | self._envvars()
        with transient_envvars({"PATH": env["PATH"]}):
            return subprocess_run(cmd, env=env, **kwargs)

    def _envvars(self) -> dict[str, str]:
        base = self.path()
        path_env = base / self._venv_bin_dir()
        path = f"{path_env}{os.pathsep}{os.environ['PATH']}"
        return {"VIRTUAL_ENV": str(base), "PATH": path}

    def _auto(self) -> list[str]:
        if Path("pyproject.toml").exists():
            return ["pip", "install", "--verbose", "."]
        if Path("requirements.txt").exists():
            return ["pip", "install", "--verbose", "-r", "requirements.txt"]
        msg = "Can't determine install command"
        raise Exception(msg)

    def _venv_bin_dir(self) -> str:
        return "Scripts" if self.platform.system == "windows" else "bin"
