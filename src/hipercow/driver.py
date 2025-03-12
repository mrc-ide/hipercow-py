import pickle
from abc import ABC, abstractmethod

from hipercow.resources import ClusterResources, TaskResources
from hipercow.root import Root
from hipercow.util import read_file_if_exists


class HipercowDriver(ABC):
    name: str

    @abstractmethod
    def __init__(self, root: Root, **kwargs):
        pass  # pragma: no cover

    @abstractmethod
    def show_configuration(self) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def submit(
        self, task_id: str, resources: TaskResources | None, root: Root
    ) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def provision(self, name: str, id: str, root: Root) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def resources(self) -> ClusterResources:
        pass  # pragma: no cover

    def task_log(
        self, task_id: str, *, outer: bool = False, root: Root
    ) -> str | None:
        if outer:
            return None
        return read_file_if_exists(root.path_task_log(task_id))


def list_drivers(root) -> list[str]:
    path = root.path_configuration(None)
    return [x.name for x in path.glob("*")]


def load_driver(driver: str | None, root: Root) -> HipercowDriver:
    dr = _load_driver(driver, root)
    if not dr:
        msg = "No driver configured"
        raise Exception(msg)
    return dr


def load_driver_optional(
    driver: str | None,
    root: Root,
) -> HipercowDriver | None:
    return _load_driver(driver, root)


def _load_driver(driver: str | None, root: Root) -> HipercowDriver | None:
    if not driver:
        return _default_driver(root)
    path = root.path_configuration(driver)
    if not path.exists():
        msg = f"No such driver '{driver}'"
        raise Exception(msg)
    with open(path, "rb") as f:
        return pickle.load(f)


def _default_driver(root: Root) -> HipercowDriver | None:
    candidates = list_drivers(root)
    n = len(candidates)
    if n == 0:
        return None
    if n > 1:
        msg = "More than one candidate driver"
        raise Exception(msg)
    return load_driver(candidates[0], root)
