from abc import ABC, abstractmethod

from pydantic import BaseModel

from hipercow import ui
from hipercow.resources import ClusterResources, TaskResources
from hipercow.root import OptionalRoot, Root, open_root
from hipercow.util import read_file_if_exists


class HipercowDriver(ABC):
    name: str

    @abstractmethod
    def __init__(self, config: BaseModel):
        pass  # pragma: no cover

    @staticmethod
    @abstractmethod
    def configure(root: Root, **kwargs) -> BaseModel:
        pass  # pragma: no cover

    @staticmethod
    @abstractmethod
    def parse_configuration(data: str) -> BaseModel:
        pass  # pragma: no cover

    @abstractmethod
    def configuration(self) -> BaseModel:
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


def show_configuration(
    name: str | None = None, root: OptionalRoot = None
) -> None:
    """Show a driver configuration.

    Args:
        name: The name of the driver.  This will be `dide` unless you
            are developing `hipercow` itself :)
        root: The root, or if not given search from the current directory.

    Returns:
        Nothing, called for side effects only.
    """
    root = open_root(root)
    dr = load_driver(name, root)
    ui.h1(f"Configuration for '{dr.name}'")
    dr.show_configuration()


def hipercow_driver(cls: type[HipercowDriver]) -> type[HipercowDriver]:
    _DRIVERS[cls.name] = cls
    return cls


_DRIVERS: dict[str, type[HipercowDriver]] = {}


# TODO: this needs a better name as we will use it internally
def _get_driver(name: str) -> type[HipercowDriver]:
    try:
        return _DRIVERS[name]
    except KeyError:
        msg = f"No such driver '{name}'"
        raise Exception(msg) from None


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


def _load_driver(name: str | None, root: Root) -> HipercowDriver | None:
    if not name:
        return _default_driver(root)
    path = root.path_configuration(name)
    if not path.exists():
        msg = f"No such driver '{name}'"
        raise Exception(msg)
    driver = _get_driver(name)
    with path.open() as f:
        data = f.read()
    return driver(driver.parse_configuration(data))


def _default_driver(root: Root) -> HipercowDriver | None:
    candidates = list_drivers(root)
    n = len(candidates)
    if n == 0:
        return None
    if n > 1:
        msg = "More than one candidate driver"
        raise Exception(msg)
    return load_driver(candidates[0], root)
