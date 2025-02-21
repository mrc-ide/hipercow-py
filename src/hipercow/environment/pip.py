import os
import subprocess
from pathlib import Path

from hipercow.environment.base import Environment, Platform
from hipercow.root import Root
from hipercow.util import subprocess_run


class Pip(Environment):
    def __init__(self, root: Root, platform: Platform, name: str):
        super().__init__(root, platform, name)

    def path(self) -> Path:
        return (
            self.root.path_environment_contents(self.name)
            / f"venv-{self.platform.system}"
        )

    def _envvars(self) -> dict[str, str]:
        base = self.path()
        path_env = base / _venv_bin_dir(self.platform.system)
        path = f"{path_env}{os.pathsep}{os.environ['PATH']}"
        return {"VIRTUAL_ENV": str(base), "PATH": path}

    def create(self, **kwargs) -> None:
        # do we need to specify the actual python version here, or do
        # we assume that we have the correct version?  If we check
        # that the version here matches that in self.platform we're ok.
        cmd = ["python", "-m", "venv", str(self.path())]
        subprocess_run(cmd, check=True, **kwargs)

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

    def provision(self, cmd: list[str] | None, **kwargs) -> None:
        self.run(self._check_args(cmd), check=True, **kwargs)

    def run(
        self,
        cmd: list[str],
        *,
        env: dict[str, str] | None = None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        env = (env or {}) | self._envvars()
        return subprocess_run(cmd, env=env, **kwargs)


def _venv_bin_dir(system: str) -> str:
    return "Scripts" if system == "windows" else "bin"
