"""Put a copy of uv onto the hipercow share for the bootstrap.

The bootstrap jobs use this copy of uv to download python and to
install hipercow, so that the cluster nodes do not need python
installed.  We use the same version of uv as is installed alongside
hipercow on the computer running the bootstrap, downloaded from uv's
releases on GitHub.  Each version lives in its own directory and is
never replaced, so a later bootstrap never changes the copy that a
running one is using.
"""

import hashlib
import importlib.metadata
import io
import os
import tarfile
import zipfile
from pathlib import Path

import requests

from hipercow import ui
from hipercow.dide.mounts import Mount

UV_RELEASES = "https://github.com/astral-sh/uv/releases/download"

UV_ARCHIVES = {
    "linux": "uv-x86_64-unknown-linux-gnu.tar.gz",
    "windows": "uv-x86_64-pc-windows-msvc.zip",
}


def uv_version() -> str:
    return importlib.metadata.version("uv")


def bootstrap_uv_path(platform: str, version: str) -> str:
    """Path to uv, relative to the bootstrap directory for `platform`."""
    exe = "uv.exe" if platform == "windows" else "uv"
    return f"uv/{version}/{exe}"


def bootstrap_uv(mount: Mount, platform: str, version: str) -> None:
    path = bootstrap_uv_path(platform, version)
    dest = mount.local / f"bootstrap-py-{platform}" / path
    if dest.exists():
        return
    ui.alert_info(f"Downloading uv {version} for {platform}")
    url = f"{UV_RELEASES}/{version}/{UV_ARCHIVES[platform]}"
    archive = _download(url)
    expected = _download(f"{url}.sha256").decode().split()[0]
    found = hashlib.sha256(archive).hexdigest()
    if found != expected:
        msg = f"Checksum of '{url}' is {found}, but expected {expected}"
        raise Exception(msg)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f"{dest.name}.partial")
    tmp.write_bytes(_extract(archive, platform))
    try:
        tmp.chmod(0o755)
    except OSError:  # pragma: no cover
        # Some network mounts don't allow this, and set permissions
        # for every file themselves.
        pass
    os.replace(tmp, dest)


def _download(url: str) -> bytes:
    res = requests.get(url, timeout=120)
    res.raise_for_status()
    return res.content


def _extract(archive: bytes, platform: str) -> bytes:
    if platform == "windows":
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            return z.read("uv.exe")
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as t:
        for m in t.getmembers():
            f = t.extractfile(m) if Path(m.name).name == "uv" else None
            if f is not None:
                return f.read()
    msg = "Did not find 'uv' in the downloaded archive"
    raise Exception(msg)
