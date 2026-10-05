"""Create conda environments using micromamba."""

import os
import shutil
import subprocess
from pathlib import Path

from hipercow.environment_engines.base import EnvironmentEngine, Platform
from hipercow.root import Root
from hipercow.util import subprocess_run

# Written into the micromamba root prefix when the environment is
# created.  Having conda-forge listed in configuration (rather than
# relying on micromamba's built-in fallback) means that channels given
# on the command line (e.g., '-c bioconda') are *added* to conda-forge
# rather than replacing it, matching the behaviour people expect from
# conda.
_MAMBARC = """channels:
  - conda-forge
"""

_CONDA_COMMANDS = {"conda", "mamba", "micromamba"}

_CONDA_SUBCOMMANDS = {"install", "update", "remove", "uninstall", "clean"}

# hipercow decides where the environment lives, so these must not be
# given by the user.
_CONDA_FORBIDDEN_ARGS = {
    "-p",
    "--prefix",
    "-n",
    "--name",
    "-r",
    "--root-prefix",
}


class Conda(EnvironmentEngine):
    """Conda environments, installed by micromamba.

    We use [micromamba](https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html),
    a single static executable, to create and manage conda
    environments.  The environment is created by path (not by name)
    within the hipercow root, so that it is visible to every node that
    can see the root.  Each environment gets its own micromamba "root
    prefix", which holds the package cache and configuration.  Only
    this configuration file is used; any `.condarc` in your home
    directory is ignored.

    The micromamba executable is found by looking first at the
    environment variable `HIPERCOW_MICROMAMBA`, and then for
    `micromamba` on the `PATH`.  On the DIDE Linux cluster the former
    is set for you.  Conda environments are not supported with the
    `dide-windows` driver, as micromamba cannot work with environments
    on a network share on Windows.

    """

    def __init__(self, root: Root, name: str, platform: Platform | None = None):
        super().__init__(root, name, platform)

    def path(self) -> Path:
        return super().path() / f"conda-{self.platform.system}"

    def path_root_prefix(self) -> Path:
        """Compute path to the micromamba root prefix.

        This holds the package cache and the micromamba configuration
        (`.mambarc`) and is kept separately for each platform,
        alongside the environment itself.

        Returns:
            The path to the micromamba root prefix.

        """
        return super().path() / f"mamba-{self.platform.system}"

    def create(self, **kwargs) -> None:
        """Create the conda environment.

        Calls

        ```
        micromamba create --yes --prefix <path>
        ```

        with the result of `path()`, creating an empty environment.
        Before doing this we write a small configuration file into
        the micromamba root prefix that selects `conda-forge` as the
        default channel.

        Args:
            **kwargs (Any): Additional arguments to `subprocess_run`

        Returns:
            Nothing, called for side effects only.
        """
        root_prefix = self.path_root_prefix()
        root_prefix.mkdir(parents=True, exist_ok=True)
        path_rc = root_prefix / ".mambarc"
        if not path_rc.exists():
            with path_rc.open("w") as f:
                f.write(_MAMBARC)
        cmd = [
            _micromamba(),
            "create",
            "--yes",
            "--prefix",
            str(self.path()),
        ]
        subprocess_run(cmd, check=True, env=self._envvars(), **kwargs)

    def check_args(self, cmd: list[str] | None) -> list[str]:
        """Validate conda installation command.

        Checks if `cmd` is a valid conda command.  The command must
        start with one of `conda`, `mamba` or `micromamba` (these are
        treated identically, and all run via micromamba) followed by
        one of `install`, `update`, `remove`, `uninstall` or `clean`.
        You must not pass `--prefix` or `--name` as hipercow manages
        the location of the environment.  Use `conda clean --all` to
        remove the package cache, which can be large.

        Alternatively, the command may start with `pip`, in which case
        it is run inside the conda environment.  This requires that
        you have already installed `pip` (and so `python`) into the
        environment.

        If `cmd` is `None` or the empty list, we try and guess a
        default command, based on files found in your project root.
        If you have an `environment.yml` (or `environment.yaml`) file
        we will run `conda install --file environment.yml`.

        Args:
            cmd: The command to validate

        Returns:
            A validated list of arguments.
        """
        if not cmd:
            return self._auto()
        if cmd[0] == "pip":
            return cmd
        if cmd[0] not in _CONDA_COMMANDS:
            msg = (
                "Expected first element of 'cmd' to be one of 'conda', "
                "'mamba', 'micromamba' or 'pip'"
            )
            raise Exception(msg)
        if len(cmd) == 1 or cmd[1] not in _CONDA_SUBCOMMANDS:
            valid = ", ".join(f"'{x}'" for x in sorted(_CONDA_SUBCOMMANDS))
            msg = f"Expected second element of 'cmd' to be one of {valid}"
            raise Exception(msg)
        for arg in cmd[2:]:
            # split to catch the '--prefix=/path' form too
            if arg.split("=")[0] in _CONDA_FORBIDDEN_ARGS:
                msg = (
                    f"Don't use '{arg}' when provisioning; hipercow "
                    "manages the location of the environment"
                )
                raise Exception(msg)
        return cmd

    def provision(self, cmd: list[str], **kwargs) -> None:
        """Provision a conda environment using micromamba.

        Args:
            cmd: The command to run, as validated by `check_args`

            **kwargs (Any): Additional arguments to `subprocess_run`

        Returns: Nothing, called for its side effect only.

        """
        if cmd[0] == "pip":
            self.run(cmd, check=True, **kwargs)
            return
        subcommand, args = cmd[1], cmd[2:]
        # 'clean' acts on the package cache (in the root prefix), not
        # the environment, and does not accept '--prefix'
        if subcommand == "clean":
            target = []
        else:
            target = ["--prefix", str(self.path())]
        cmd_mm = [_micromamba(), subcommand, "--yes", *target, *args]
        subprocess_run(cmd_mm, check=True, env=self._envvars(), **kwargs)

    def run(
        self,
        cmd: list[str],
        *,
        env: dict[str, str] | None = None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        """Run a command within the conda environment.

        We use `micromamba run`, which activates the environment
        (setting `PATH`, `CONDA_PREFIX` and running any activation
        scripts provided by packages) before running `cmd`.

        Args:
            cmd: The command to run

            env: Environment variables, passed into `subprocess_run`.

            **kwargs (Any): Keyword arguments to `subprocess_run`.

        Returns: Details about the process, if `check=True` is not
           present in `kwargs`
        """
        cmd_mm = [_micromamba(), "run", "--prefix", str(self.path()), *cmd]
        env = (env or {}) | self._envvars()
        return subprocess_run(cmd_mm, env=env, **kwargs)

    def _envvars(self) -> dict[str, str]:
        # Pointing both MAMBARC and CONDARC at our configuration
        # means that micromamba reads *only* this file, and not any
        # ~/.condarc that the user has lying around (which might
        # contain the 'defaults' channel, which mixes badly with
        # conda-forge).
        root_prefix = self.path_root_prefix()
        path_rc = str(root_prefix / ".mambarc")
        return {
            "MAMBA_ROOT_PREFIX": str(root_prefix),
            "MAMBARC": path_rc,
            "CONDARC": path_rc,
        }

    def _auto(self) -> list[str]:
        for filename in ["environment.yml", "environment.yaml"]:
            if Path(filename).exists():
                return ["conda", "install", "--file", filename]
        msg = "Can't determine install command"
        raise Exception(msg)


def _micromamba() -> str:
    path = os.environ.get("HIPERCOW_MICROMAMBA")
    if path:
        if not Path(path).exists():
            msg = (
                f"'HIPERCOW_MICROMAMBA' is set to '{path}', but this "
                "does not exist"
            )
            raise Exception(msg)
        return path
    path = shutil.which("micromamba")
    if path:
        return path
    msg = (
        "Could not find 'micromamba'; set the environment variable "
        "'HIPERCOW_MICROMAMBA' to its location or add it to the PATH"
    )
    raise Exception(msg)
