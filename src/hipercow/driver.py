from abc import ABC, abstractmethod

from hipercow.root import Root


class HipercowDriver(ABC):
    name: str

    @abstractmethod
    def __init__(self, root: Root, **kwargs):
        pass  # pragma: no cover

    def submit(self, task_id: str, root: Root) -> None:
        pass  # pragma: no cover

    def provision(self, root: Root, name: str, cmd: list[str] | None) -> None:
        pass  # pragma: no cover
