import os
import subprocess
from pathlib import Path

from hipercow.environment_engines.base import EnvironmentEngine, Platform
from hipercow.root import Root
from hipercow.util import subprocess_run, transient_envvars


class Pip(EnvironmentEngine):
    def __init__(self, root: Root, name: str, platform: Platform | None = None):
        super().__init__(root, name, platform)

    def path(self) -> Path:
        return (
            self.root.path_environment_contents(self.name)
            / f"venv-{self.platform.system}"
        )

    def create(self, **kwargs) -> None:
        # do we need to specify the actual python version here, or do
        # we assume that we have the correct version?  If we check
        # that the version here matches that in self.platform we're ok.
        cmd = ["python", "-m", "venv", str(self.path())]
        subprocess_run(cmd, check=True, **kwargs)

    def provision(self, cmd: list[str] | None, **kwargs) -> None:
        self.run(self._check_args(cmd), check=True, **kwargs)

    def run(
        self,
        cmd: list[str],
        *,
        env: dict[str, str] | None = None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
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
        path_old = os.environ["PATH"]
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

    def _check_args(self, cmd: list[str] | None) -> list[str]:
        if not cmd:
            return self._auto()
        if cmd[0] != "pip":
            msg = "Expected first element of 'cmd' to be 'pip'"
            raise Exception(msg)
        return cmd

    def _venv_bin_dir(self) -> str:
        return "Scripts" if self.platform.system == "windows" else "bin"
