from taskwait import Task, taskwait

from hipercow.dide.auth import fetch_credentials
from hipercow.dide.batch import write_batch_provision, write_batch_task_run
from hipercow.dide.mounts import Mount, PathMap, detect_mounts, remap_path
from hipercow.dide.web import DideWebClient
from hipercow.driver import HipercowDriver
from hipercow.root import Root
from hipercow.util import check_python_version


class DideConfiguration:
    path_map: PathMap
    python_version: str

    def __init__(
        self, root: Root, *, mounts: list[Mount], python_version: str | None
    ):
        self.path_map = remap_path(root.path, mounts)
        self.python_version = check_python_version(python_version)


class DideDriver(HipercowDriver):
    name = "dide"
    config: DideConfiguration

    def __init__(self, root: Root, **kwargs):
        mounts = detect_mounts()
        self.config = DideConfiguration(root, mounts=mounts, **kwargs)

    def show_configuration(self) -> None:
        path_map  = self.config.path_map
        print(f"path mapping:")
        print(f"  drive: {path_map.remote}")
        print(f"  share: \\\\{path_map.mount.host}\\{path_map.mount.remote}")
        print(f"python version: {self.config.python_version}")

    def submit(self, task_id: str, root: Root) -> None:
        cl = _web_client()
        unc = write_batch_task_run(task_id, self.config.path_map, root)
        cl.submit(unc, task_id)

    def provision(self, root: Root, name: str, id: str) -> None:
        _dide_provision(root, name, id, self.config.path_map)


class ProvisionWaitWrapper(Task):
    def __init__(
        self,
        root: Root,
        name: str,
        provision_id: str,
        client: DideWebClient,
        dide_id: str,
    ):
        self.root = root
        self.name = name
        self.provision_id = provision_id
        self.client = client
        self.dide_id = dide_id
        self.status_waiting = {"created", "submitted"}
        self.status_running = {"running"}

    def status(self) -> str:
        return str(self.client.status_job(self.dide_id))

    def log(self) -> list[str] | None:
        path = self.root.path_provision_log(self.name, self.provision_id)
        if not path.exists():
            return None
        with path.open() as f:
            return f.read().splitlines()

    def has_log(self) -> bool:
        return True


def _web_client() -> DideWebClient:
    credentials = fetch_credentials()
    cl = DideWebClient(credentials)
    cl.login()
    return cl


def _dide_provision(root: Root, name: str, id: str, path_map: PathMap):
    cl = _web_client()
    unc = write_batch_provision(name, id, path_map, root)
    dide_id = cl.submit(unc, f"{name}/{id}")
    task = ProvisionWaitWrapper(root, name, id, cl, dide_id)
    taskwait(task)
