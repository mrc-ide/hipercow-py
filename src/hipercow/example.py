from hipercow.driver import HipercowDriver
from hipercow.root import Root


class ExampleDriver(HipercowDriver):
    name = "example"

    def __init__(self, root: Root, **kwargs):
        pass

    def submit(self, task_id, root: Root) -> None:  # noqa: ARG002
        print(f"submitting '{task_id}'")
