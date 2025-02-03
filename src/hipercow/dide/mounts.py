import csv
import platform
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Mount:
    host: str
    remote: Path
    local: Path

    def __post_init__(self):
        self.remote = Path(self.remote)
        self.local = Path(self.local)


@dataclass
class PathMap:
    path: Path
    mount: Mount
    remote: Path
    relative: Path


def remap_path(path: Path, mounts: list[Mount]) -> PathMap:
    pos = [m for m in mounts if path.is_relative_to(m.local)]
    if len(pos) > 1:
        msg = "More than one plausible mount for local directory"
        raise Exception(msg)
    elif len(pos) == 0:
        msg = "Can't map local directory '{path}' to network path"
        raise Exception(msg)
    mount = pos[0]
    relative = path.relative_to(mount.local)
    if m := re.match("^([A-Za-z]:)[/\\\\]?$", str(mount.local)):
        remote = Path(m.group(1))
    elif mount.host == "qdrive":
        remote = Path("Q:")
    else:
        remote = Path("V:")
    return PathMap(
        path, mount, remote, Path(_drop_leading_slash(str(relative)))
    )


def detect_mounts() -> list[Mount]:
    if platform.system() == "Windows":
        return _detect_mounts_windows()
    else:
        return _detect_mounts_unix()


def _detect_mounts_unix() -> list[Mount]:
    fstype = _unix_smb_mount_type(platform.system())
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

    return Mount(_clean_dide_hostname(host), Path(remote), Path(local))


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
        _clean_dide_hostname(host), Path(remote), Path(_forward_slash(local))
    )


def _clean_dide_hostname(host: str) -> str:
    return re.sub("\\.dide\\.ic\\.ac\\.uk$", "", host)


def _forward_slash(x: str) -> str:
    return x.replace("\\", "/")


def _drop_leading_slash(x: str) -> str:
    return re.sub("^[/\\\\]", "", x)
