import subprocess
from pathlib import Path

from hipercow.environment.base import Environment, Platform
from hipercow.root import Root
from hipercow.util import subprocess_run


class Empty(Environment):
    def __init__(self, root: Root, platform: Platform, name: str):
        super().__init__(root, platform, name)

    def path(self) -> Path:
        return self.root.path_environment(self.name)

    def create(self) -> None:
        pass

    def provision(self, cmd: list[str] | None) -> None:
        pass

    def run(
        self,
        cmd: list[str],
        *,
        filename: Path | None = None,
        env: dict[str, str] | None = None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        return subprocess_run(cmd, filename=filename, env=env or {}, **kwargs)
