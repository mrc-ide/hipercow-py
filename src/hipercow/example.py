from hipercow.driver import DriverConfiguration, HipercowDriver
from hipercow.provision import provision_run
from hipercow.resources import ClusterResources, Queues, TaskResources
from hipercow.root import Root
from hipercow.util import check_python_version


class ExampleConfiguration(DriverConfiguration):
    python_version: str


class ExampleDriver(HipercowDriver):
    name = "example"

    def __init__(self, root: Root, config: ExampleConfiguration):
        self.config = config

    @staticmethod
    def configure(root: Root, **kwargs) -> ExampleConfiguration:
        version = kwargs.get("python_version")
        if isinstance(version, str):
            requested = check_python_version(version)
            local = check_python_version(None)
            if local != requested:
                msg = (
                    f"Requested python version {version}"
                    f"is not the same as the local version {local}"
                )
                raise Exception(msg)
        return ExampleConfiguration(python_version)
        

    def show_configuration(self) -> None:
        print("(no configuration)")

    def submit(
        self,
        task_id: str,
        resources: TaskResources | None,  # noqa: ARG002
        root: Root,  # noqa: ARG002
    ) -> None:
        print(f"submitting '{task_id}'")

    def provision(self, name: str, id: str, root: Root) -> None:
        provision_run(name, id, root)

    def resources(self) -> ClusterResources:
        return ClusterResources(
            queues=Queues.simple("default"),
            max_cores=1,
            max_memory=32,
        )
