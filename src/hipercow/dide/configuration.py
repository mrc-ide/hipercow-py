from hipercow.dide.mounts import Mount, PathMap, remap_path
from hipercow.driver import DriverConfiguration
from hipercow.root import Root
from hipercow.util import check_python_version


class DideConfiguration(DriverConfiguration):
    path_map: PathMap
    python_version: str

    def __init__(
        self,
        root: Root,
        *,
        mounts: list[Mount],
        python_version: str | None = None,
    ):
        self.path_map = remap_path(root.path, mounts)
        self.python_version = check_python_version(python_version)
