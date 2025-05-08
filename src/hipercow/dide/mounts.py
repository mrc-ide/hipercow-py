import csv
import platform
import re
import subprocess
from pathlib import Path

from pydantic import BaseModel


# We use 'str' here and not 'Path' because we are interested in
# storing paths that might be of a different type to the host
# operating system (e.g., a windows path while running on a linux
# system, or v.v.). The pathlib package tries to give us posix
# semantics for windows paths and won't let us construct a path of a
# different type than the host system, which means things like leading
# and trailing slashes or forward slashes vs backslashes become hard
# to reason about.
class Mount(BaseModel):
    """The name of the host on which the mount is found."""

    host: str
    """The path of the mount on the host. For windows hosts this will
    be a drive letter, while on unix hosts this will be an absolute
    path (really for both this is an absolute path but convention at
    least means that they're always drives on windows)"""
    remote: str
    """The path on the local machine - i.e., where the network mount
    is found on the machine calling hipercow. This one could actually
    be a Path object and we might move to that.  On windows this is a
    drive letter"""
    local: Path


class PathMap(BaseModel):
    """The mapping between a local path and one on a remote share."""

    path: Path
    """This is the mount that the file can be found on"""
    mount: Mount
    """The location (drive or absolute path) that 'mount' is found on
    the remote machine. This is stored as a 'str' like Mount's
    components, because this must be able to represent a path on a
    different platform to the one currently running hipercow's code"""
    remote: str
    """The path relative to the mount.  We'll make this a str,
    and not a Path, too as this makes testing and reasoning a bit
    easier.  We never include a leading slash but one is implicit on
    windows, and we always store in forward slash form"""
    relative: str


def remap_path(path: Path, mounts: list[Mount]) -> PathMap:
    pos = [m for m in mounts if path.is_relative_to(m.local)]
    if len(pos) > 1:
        msg = "More than one plausible mount for local directory"
        raise Exception(msg)
    elif len(pos) == 0:
        msg = f"Can't map local directory '{path}' to network path"
        raise Exception(msg)
    mount = pos[0]
    relative = path.relative_to(mount.local)
    relative_str = _forward_slash(_drop_leading_slash(str(relative)))

    if m := re.match("^([A-Za-z]:)[/\\\\]?$", str(mount.local)):
        remote = m.group(1).upper()
    elif mount.host in ["qdrive", "wpia-san04"]:
        remote = "Q:"
    else:
        remote = "V:"

    return PathMap(path=path, mount=mount, remote=remote, relative=relative_str)


def detect_mounts() -> list[Mount]:
    system = platform.system()
    if system == "Windows":
        return _detect_mounts_windows()
    else:
        return _detect_mounts_unix(system)


def _detect_mounts_unix(system: str) -> list[Mount]:
    fstype = _unix_smb_mount_type(system)
    res = subprocess.run(
        ["mount", "-t", fstype], capture_output=True, check=True
    )
    txt = res.stdout.decode("utf-8")
    return [_parse_unix_mount_entry(x) for x in txt.splitlines()]


def _unix_smb_mount_type(platform: str) -> str:
    return "cifs" if platform == "Linux" else "smbfs"


def _parse_unix_mount_entry(x: str) -> Mount:
    pat = re.compile("^//([^@]*@)?([^/]*)/(.*?)\\s+on\\s+(.*?) (.+)$")
    m = pat.match(x)
    if not m:
        msg = f"Failed to match mount output '{x}'"
        raise Exception(msg)

    _, host, remote, local, _ = m.groups()

    return Mount(
        host=_clean_dide_hostname(host), remote=remote, local=Path(local)
    )


def _detect_mounts_windows() -> list[Mount]:
    res = subprocess.run(
        ["powershell", "-c", "Get-SmbMapping|ConvertTo-CSV"],
        capture_output=True,
        check=True,
    )
    txt = res.stdout.decode("utf-8")
    return _parse_windows_mount_output(txt)


def _parse_windows_mount_output(txt: str) -> list[Mount]:
    d = list(csv.reader(txt.splitlines()[1:]))
    header = d[0]
    i_status = header.index("Status")
    i_local = header.index("LocalPath")
    i_remote = header.index("RemotePath")
    return [
        _parse_windows_mount_entry(x[i_local], x[i_remote])
        for x in d[1:]
        if x[i_status] == "OK"
    ]


def _parse_windows_mount_entry(local: str, remote: str) -> Mount:
    m = re.match("^//([^/]+)/(.+)$", _forward_slash(remote))
    if not m:
        msg = "Failed to parse windows entry"
        raise Exception(msg)
    host, remote = m.groups()
    return Mount(
        host=_clean_dide_hostname(host), remote=remote, local=Path(local + "/")
    )


def _clean_dide_hostname(host: str) -> str:
    return re.sub("\\.dide\\.ic\\.ac\\.uk$", "", host)


def _forward_slash(x: str) -> str:
    return x.replace("\\", "/")


def _backward_slash(x: str) -> str:
    return x.replace("/", "\\")


def _drop_leading_slash(x: str) -> str:
    return re.sub("^[/\\\\]", "", x)
