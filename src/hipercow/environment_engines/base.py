import platform
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from hipercow.root import Root


# We don't want to call actual 'platform' code very often because our
# intent is that we're generating things for another system.
@dataclass
class Platform:
    system: str
    version: str

    @staticmethod
    def local() -> "Platform":
        return Platform(platform.system().lower(), platform.python_version())


class EnvironmentEngine(ABC):
    def __init__(self, root: Root, name: str, platform: Platform | None = None):
        self.root = root
        self.name = name
        self.platform = platform or Platform.local()

    def exists(self) -> bool:
        return self.path().exists()

    @abstractmethod
    def path(self) -> Path:
        pass  # pragma: no cover

    @abstractmethod
    def create(self, **kwargs) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def provision(self, cmd: list[str] | None, **kwargs) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def run(
        self,
        cmd: list[str],
        *,
        env: dict[str, str] | None = None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        pass  # pragma: no cover
