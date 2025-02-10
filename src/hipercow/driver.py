import pickle
from abc import ABC, abstractmethod

from hipercow.root import Root
from hipercow.util import transient_working_directory


class HipercowDriver(ABC):
    name: str

    @abstractmethod
    def __init__(self, root: Root, **kwargs):
        pass

    def submit(self, task_id: str, root: Root) -> None:
        pass


class ExampleDriver(HipercowDriver):
    name = "example"

    def __init__(self, root: Root, **kwargs):
        pass

    def submit(self, task_id, root: Root) -> None:
        print(f"submitting '{task_id}'")


def configure(root: Root, driver: type[HipercowDriver], **kwargs):
    with transient_working_directory(root.path):
        config = driver(**kwargs)

    path = root.path_configuration(driver.name)
    exists = path.exists()
    with path.open("wb") as f:
        pickle.dump(config, f)
    if exists:
        print("Updated configuration for '{driver.name}'")
    else:
        print("Configured hipercow to use '{driver.name}'")
