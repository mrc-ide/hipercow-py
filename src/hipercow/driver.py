import pickle
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


def load_driver(
    root: Root, driver: str | None, *, allow_none: bool = False
) -> HipercowDriver | None:
    if not driver:
        return _default_driver(root, allow_none=allow_none)
    path = root.path_configuration(driver)
    if not path.exists():
        msg = f"No such driver '{driver}'"
        raise Exception(msg)
    with open(path, "rb") as f:
        return pickle.load(f)


def _default_driver(
    root: Root, *, allow_none: bool = False
) -> HipercowDriver | None:
    candidates = root.list_drivers()
    n = len(candidates)
    if n == 0:
        if not allow_none:
            msg = "No driver configured"
            raise Exception(msg)
        return None
    if n > 1:
        msg = "More than one candidate driver"
        raise Exception(msg)
    return load_driver(root, candidates[0])
