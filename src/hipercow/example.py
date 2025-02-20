from hipercow.driver import HipercowDriver
from hipercow.environment import Platform, engine
from hipercow.root import Root
from hipercow.util import transient_working_directory


class ExampleDriver(HipercowDriver):
    name = "example"

    def __init__(self, root: Root, **kwargs):
        pass

    def submit(self, task_id, root: Root) -> None:  # noqa: ARG002
        print(f"submitting '{task_id}'")

    def provision(self, root: Root, name: str, cmd: list[str] | None) -> None:
        platform = Platform.local()
        pr = engine(root, platform, name)
        if not pr.exists():
            pr.create()
        with transient_working_directory(root.path):
            pr.provision(cmd)
