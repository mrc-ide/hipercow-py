from pathlib import Path

from hipercow import ui
from hipercow.dide.auth import fetch_credentials
from hipercow.dide.batch_linux import (
    _dide_provision_linux,
    write_batch_task_run_linux,
)
from hipercow.dide.batch_windows import (
    _dide_provision_win,
    write_batch_task_run_win,
)
from hipercow.dide.configuration import DideConfiguration, dide_configuration
from hipercow.dide.mounts import detect_mounts
from hipercow.dide.web import DideWebClient
from hipercow.driver import HipercowDriver, hipercow_driver
from hipercow.resources import ClusterResources, Queues, TaskResources
from hipercow.root import Root


@hipercow_driver
class DideWindowsDriver(HipercowDriver):
    name = "dide-windows"
    config: DideConfiguration

    def __init__(self, config: DideConfiguration):
        self.config = config

    @staticmethod
    def configure(root: Root, **kwargs) -> DideConfiguration:
        mounts = detect_mounts()
        return dide_configuration(root, mounts=mounts, **kwargs)

    @staticmethod
    def parse_configuration(data: str) -> DideConfiguration:
        return DideConfiguration.model_validate_json(data)

    def configuration(self) -> DideConfiguration:
        return self.config

    def show_configuration(self) -> None:
        path_map = self.config.path_map
        ui.li("[bold]Path mapping[/bold]")
        ui.li(f"drive '{path_map.remote}'", indent=2, symbol="-")
        ui.li(
            f"share '\\\\{path_map.mount.host}\\{path_map.mount.remote}'",
            indent=2,
            symbol="-",
        )
        ui.li(f"[bold]Python version[/bold]: {self.config.python_version}")

    def submit(
        self, task_id: str, resources: TaskResources | None, root: Root
    ) -> None:
        cl = _web_client()
        unc = write_batch_task_run_win(task_id, self.config, root)
        if not resources:
            resources = self.resources().validate_resources(TaskResources())
        dide_id = cl.submit(unc, task_id, resources=resources)
        with self._path_dide_id(task_id, root).open("w") as f:
            f.write(dide_id)

    def provision(self, name: str, id: str, root: Root) -> None:
        _dide_provision_win(name, id, self.config, _web_client(), root)

    def resources(self) -> ClusterResources:
        # We should get this from the cluster itself but with caching
        # not yet configured this seems unwise as we'll hit the
        # cluster an additional time for every job submission rather
        # than just once a session.
        queues = Queues(
            {"AllNodes", "BuildQueue", "Testing"},
            default="AllNodes",
            test="Testing",
            build="BuildQueue",
        )
        return ClusterResources(queues=queues, max_cores=32, max_memory=512)

    def task_log(
        self, task_id: str, *, outer: bool = False, root: Root
    ) -> str | None:
        if outer:
            with self._path_dide_id(task_id, root).open() as f:
                dide_id = f.read().strip()
            cl = _web_client()
            return cl.log(dide_id.strip())
        return super().task_log(task_id, outer=False, root=root)

    def _path_dide_id(self, task_id: str, root: Root) -> Path:
        return root.path_task(task_id) / "dide_id"


@hipercow_driver
class LinuxWindowsDriver(HipercowDriver):
    name = "dide-linux"
    config: DideConfiguration

    def __init__(self, config: DideConfiguration):
        self.config = config

    @staticmethod
    def configure(root: Root, **kwargs) -> DideConfiguration:
        mounts = detect_mounts()
        return dide_configuration(root, mounts=mounts, **kwargs)

    @staticmethod
    def parse_configuration(data: str) -> DideConfiguration:
        return DideConfiguration.model_validate_json(data)

    def configuration(self) -> DideConfiguration:
        return self.config

    def show_configuration(self) -> None:
        path_map = self.config.path_map
        ui.li("[bold]Path mapping[/bold]")
        ui.li(f"drive '{path_map.remote}'", indent=2, symbol="-")
        ui.li(
            f"share '\\\\{path_map.mount.host}\\{path_map.mount.remote}'",
            indent=2,
            symbol="-",
        )
        ui.li(f"[bold]Python version[/bold]: {self.config.python_version}")

    def submit(
        self, task_id: str, resources: TaskResources | None, root: Root
    ) -> None:
        cl = _web_client()
        linux_path = write_batch_task_run_linux(task_id, self.config, root)
        if not resources:
            resources = self.resources().validate_resources(TaskResources())
        dide_id = cl.submit(linux_path, task_id, resources=resources)
        with self._path_dide_id(task_id, root).open("w") as f:
            f.write(dide_id)

    def provision(self, name: str, id: str, root: Root) -> None:
        _dide_provision_linux(name, id, self.config, _web_client(), root)

    def resources(self) -> ClusterResources:
        # We should get this from the cluster itself but with caching
        # not yet configured this seems unwise as we'll hit the
        # cluster an additional time for every job submission rather
        # than just once a session.
        queues = Queues(
            {"LinuxNodes"},
            default="LinuxNodes",
            test="LinuxNodes",
            build="LinuxNodes",
        )
        return ClusterResources(queues=queues, max_cores=32, max_memory=512)

    def task_log(
        self, task_id: str, *, outer: bool = False, root: Root
    ) -> str | None:
        if outer:
            with self._path_dide_id(task_id, root).open() as f:
                dide_id = f.read().strip()
            cl = _web_client()
            return cl.log(dide_id.strip())
        return super().task_log(task_id, outer=False, root=root)

    def _path_dide_id(self, task_id: str, root: Root) -> Path:
        return root.path_task(task_id) / "dide_id"


def _web_client() -> DideWebClient:
    credentials = fetch_credentials()
    cl = DideWebClient(credentials)
    cl.login()
    return cl
