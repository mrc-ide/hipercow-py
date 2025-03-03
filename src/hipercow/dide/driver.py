from dataclasses import dataclass

import taskwait

from hipercow.dide.auth import fetch_credentials
from hipercow.dide.batch import write_batch_provision, write_batch_task_run
from hipercow.dide.mounts import PathMap, detect_mounts, remap_path
from hipercow.dide.web import DideWebClient
from hipercow.driver import HipercowDriver
from hipercow.root import Root

# Ignoring for now the need to get a different version of this for
# each machine that submits (see for example the R version of this).
# Better might be to allow interleaving old and new configurations
# together somehow, but that's quite weird.


@dataclass
class DideConfiguration:
    path_map: PathMap


class DideDriver(HipercowDriver):
    name = "dide"
    config: DideConfiguration

    def __init__(self, root: Root, **kwargs):  #  noqa: ARG002
        mounts = detect_mounts()
        path = remap_path(root.path, mounts)
        self.config = DideConfiguration(path)

    def submit(self, task_id: str, root: Root):
        credentials = fetch_credentials()
        cl = DideWebClient(credentials)
        cl.login()
        unc = write_batch_task_run(task_id, self.config.path_map, root)
        cl.submit(unc, task_id)

    def provision(self, root: Root, name: str, id: str) -> None:
        credentials = fetch_credentials()
        cl = DideWebClient(credentials)
        cl.login()
        unc = write_batch_provision(name, id, self.config.path_map, root)
        dide_id = cl.submit(unc, f"{name}/{id}")
        ProvisionWaitWrapper(root, name, id, cl, dide_id)
        # Once we have support, we need to block here and stream logs,
        # but that erquires getting the logwatch functionality ported
        # over.
        print("A provisioning task has been submitted")
        print("Have a look at the web portal to keep track on progress")


class ProvisionWaitWrapper(taskwait.Task):
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
            return f.readlines()

    def has_log(self) -> bool:
        return True
