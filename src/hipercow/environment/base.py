import platform
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


class Environment(ABC):
    def __init__(self, root: Root, platform: Platform, name: str):
        self.root = root
        self.platform = platform
        self.name = name

    def exists(self) -> bool:
        return self.path().exists()

    @abstractmethod
    def path(self) -> Path:
        pass  # pragma: no cover

    @abstractmethod
    def create(self) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def provision(self, cmd: list[str] | None) -> None:
        pass  # pragma: no cover
