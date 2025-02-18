from abc import ABC, abstractmethod
from pathlib import Path


class Environment(ABC):

    @abstractmethod
    def __init__(self):
        pass  # pragma no cover

    @abstractmethod
    def path(self, name: str) -> Path:
        pass  # pragma no cover

    @abstractmethod
    def create(self, name: str) -> list[str]:
        pass  # pragma no cover

    @abstractmethod
    def activate(self, name: str, platform: str) -> list[str]:
        pass  # pragma no cover

    @abstractmethod
    def install(self) -> list[str]:
        pass  # pragma no cover
