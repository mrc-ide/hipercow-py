from hipercow.driver import HipercowDriver
from hipercow.provision import provision_run
from hipercow.root import Root


class ExampleDriver(HipercowDriver):
    name = "example"

    def __init__(self, root: Root, **kwargs):
        pass

    def show_configuration(self) -> None:
        print("(no configuration)")

    def submit(self, task_id, root: Root) -> None:  # noqa: ARG002
        print(f"submitting '{task_id}'")

    def provision(self, root: Root, name: str, id: str) -> None:
        provision_run(root, name, id)
