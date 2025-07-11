from pydantic import BaseModel

from hipercow import ui
from hipercow.driver import HipercowDriver, hipercow_driver
from hipercow.provision import provision_run
from hipercow.resources import ClusterResources, Queues, TaskResources
from hipercow.root import Root
from hipercow.util import check_python_version


class ExampleDriverConfiguration(BaseModel):
    pass


def example_configuration(**kwargs) -> ExampleDriverConfiguration:
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
    return ExampleDriverConfiguration()


@hipercow_driver
class ExampleDriver(HipercowDriver):
    name = "example"
    config: ExampleDriverConfiguration

    def __init__(self, config: ExampleDriverConfiguration):
        self.config = config

    @staticmethod
    def configure(
        root: Root,  # noqa: ARG004
        **kwargs,
    ) -> ExampleDriverConfiguration:
        return example_configuration(**kwargs)

    @staticmethod
    def parse_configuration(data: str) -> ExampleDriverConfiguration:
        return ExampleDriverConfiguration.model_validate_json(data)

    def configuration(self) -> BaseModel:
        return self.config

    def show_configuration(self) -> None:
        ui.text("[dim](no configuration)[/dim]")

    def submit(
        self,
        task_id: str,
        resources: TaskResources | None,  # noqa: ARG002
        root: Root,  # noqa: ARG002
    ) -> None:
        ui.alert_info(f"submitting '{task_id}'")

    def provision(self, name: str, id: str, root: Root) -> None:
        provision_run(name, id, root)

    def resources(self) -> ClusterResources:
        return ClusterResources(
            queues=Queues.simple("default"),
            max_cores=1,
            max_memory=32,
        )
