import pickle
import platform
from abc import ABC, abstractmethod

from hipercow.root import Root


class HipercowDriver(ABC):
    name: str

    @abstractmethod
    def __init__(self, root: Root, **kwargs):
        pass  # pragma: no cover

    @abstractmethod
    def submit(self, task_id: str, root: Root) -> None:
        pass  # pragma: no cover

    @abstractmethod
    def provision(self, root: Root, name: str, id: str) -> None:
        pass  # pragma: no cover


def list_drivers(root) -> list[str]:
    hostname = platform.node()
    path = root.path / "hipercow" / "config" / hostname
    return [x.name for x in path.glob("*")]


def load_driver(root: Root, driver: str | None) -> HipercowDriver:
    dr = _load_driver(root, driver)
    if not dr:
        msg = "No driver configured"
        raise Exception(msg)
    return dr


def load_driver_optional(
    root: Root, driver: str | None
) -> HipercowDriver | None:
    return _load_driver(root, driver)


def _load_driver(root: Root, driver: str | None) -> HipercowDriver | None:
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
    return load_driver(root, candidates[0])
