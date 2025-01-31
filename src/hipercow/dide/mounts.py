from dataclasses import dataclass
from pathlib import Path
import platform
import subprocess
import re


@dataclass
class Mount:
    host: str
    remote: Path
    local: Path


def detect_mounts() -> list[Mount]:
    if platform.system() == "Windows":
        return _detect_mounts_windows()
    else:
        return _detect_mounts_unix()


def _detect_mounts_unix() -> list[Mount]:
    fstype = _unix_smb_mount_type(platform.system())
    res = subprocess.run(
        ["mount", "-t", fstype],
        capture_output=True,
        check=True
    )
    txt = res.stdout.decode("utf-8")
    return [_parse_unix_mount_entry(x) for x in txt.strip().splitlines()]


def _unix_smb_mount_type(platform: str) -> str:
    return "cifs" if platform == "Linux" else "smbfs"


def _parse_unix_mount_entry(x: str) -> Mount:
    pat = re.compile("^//([^@]*@)?([^/]*)/(.*?)\\s+on\\s+(.*?) (.+)$")
    m = pat.match(x)
    if not m:
        msg = f"Failed to match mount outout '{x}'"
        raise Exception(msg)

    _, host, remote, local, _ = m.groups()

    return Mount(_clean_dide_hostname(host), remote, local)


def _detect_mounts_windows() -> list[Mount]:
     mounts_str = subprocess.run(
         ["powershell", "-c", "Get-SmbMapping|ConvertTo-CSV"],
         capture_output=True
     )
     return [_parse_windows_mount_entry(x) for x in mounts_str[-1]]


def _parse_windows_mount_entry(x: str) -> Mount:
    return Mount(_clean_dide_hostname(host), remote, local)


def _clean_dide_hostname(host: str) -> str:
    return re.sub("dide\\.ic\\.ac\\.uk$", "", host)
