from abc import ABC, abstractmethod

from hipercow.root import Root


class HipercowDriver(ABC):
    name: str

    @abstractmethod
    def __init__(self, root: Root, **kwargs):
        pass

    def submit(self, task_id: str, root: Root) -> None:
        pass
