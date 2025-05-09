from pydantic import BaseModel

from hipercow.dide.auth import check as check_auth
from hipercow.dide.mounts import Mount, PathMap, remap_path
from hipercow.root import Root
from hipercow.util import check_python_version


class DideConfiguration(BaseModel):
    path_map: PathMap
    python_version: str


def dide_configuration(
    root: Root,
    *,
    mounts: list[Mount],
    python_version: str | None = None,
    check_credentials: bool = True,
) -> DideConfiguration:
    if check_credentials:
        check_auth()
    path_map = remap_path(root.path, mounts)
    python_version = check_python_version(python_version)
    return DideConfiguration(path_map=path_map, python_version=python_version)
