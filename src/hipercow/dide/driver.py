from dataclasses import dataclass

from hipercow.dide.auth import fetch_credentials
from hipercow.dide.batch import write_batch_task_run
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

    def proivision(self, root: Root, name: str) -> None:
        raise NotImplementedError()
