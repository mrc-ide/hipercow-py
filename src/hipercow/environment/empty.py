import subprocess
from pathlib import Path

from hipercow.environment.base import Environment, Platform
from hipercow.root import Root


class Empty(Environment):
    def __init__(self, root: Root, platform: Platform, name: str):
        super().__init__(root, platform, name)

    def exists(self) -> bool:
        return True

    def path(self) -> Path:
        return self.root.path_environment(self.name)

    def create(self, **kwargs) -> None:
        pass

    def provision(self, cmd: list[str] | None, **kwargs) -> None:
        pass

    # These "unused argument" errors from ruff are probably a bug?
    def run(
        self,
        cmd: list[str],  # noqa: ARG002
        *,
        env: dict[str, str] | None = None,  # noqa: ARG002
        **kwargs,  # noqa: ARG002
    ) -> subprocess.CompletedProcess:
        msg = "Can't provision an empty environment!"
        raise Exception(msg)
