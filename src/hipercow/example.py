from hipercow.driver import HipercowDriver
from hipercow.environment import Platform, provider
from hipercow.root import Root


class ExampleDriver(HipercowDriver):
    name = "example"

    def __init__(self, root: Root, **kwargs):
        pass

    def submit(self, task_id, root: Root) -> None:  # noqa: ARG002
        print(f"submitting '{task_id}'")

    def provision(self, root: Root, name: str, cmd: list[str] | None) -> None:
        platform = Platform.local()
        pr = provider(root, platform, name)
        if not pr.exists():
            pr.create()
        pr.provision(cmd)
