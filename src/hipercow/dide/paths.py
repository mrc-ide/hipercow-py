from dataclasses import dataclass
from pathlib import Path
from hipercow.dide.mounts import Mount

@dataclass
class PathMap:
    local: Path
    remote: Path
    relative: Path


# The first stage here should be mapping the mounts onto where they
# are on the cluster.  For the windows cluster this is simply a series
# of drives. For things that can't be mounted we can use a singleton
# or None
#
# Store the pair in a dictionary keyed by the local mounts
class DidePath:
    def __init__(self, mounts: list[Mount]):
        self.mounts = mounts
        
        

    def remote_path(self, path: Path) -> Path:
        res = self.prepare_path(path)
        return res.drive_remote / res.rel

    def prepare_path(self, path: Path) -> Any:
        if not path.exists():
            msg = f"Path does not exist '{path}'"
            raise Exception(msg)
        m = _remap_path(path, mounts)        


def dide_cluster_paths(path: Path, mounts: list[Mount]) -> Any:
    m = _remap_path(path, mounts)
    # What do we need to know here?
    # We need enough to be able to do remote_path and prepare_path

    pos = [m for m in mounts if path.is_relative_to(m.local)]
    
    


# This is the mapping for the user -> remote mapping.  We'll then need
# to do this remote -> hpc mapping second but using this information.
# This is the point where we need to consider available drive letters
# etc.

def _remap_path(path: Path, mounts: list[Mount]) -> PathMap:
    pos = [m for m in mounts if path.is_relative_to(m.local)]
    if len(pos) > 1:
        msg = "More than one plausible mount for local directory"
        raise Exception(msg)
    elif len(pos) == 0:
        msg = "Can't map local directory '{path}' to network path"
        raise Exception(msg)
    mount = pos[0]
    relative = path.relative_to(mount.local)
    return PathMap(mount.local, mount.remote, relative)

