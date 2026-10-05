import hashlib
import importlib.metadata
import io
import os
import sys
import tarfile
import zipfile

import pytest
import responses

from hipercow.dide import bootstrap_uv
from hipercow.dide.mounts import Mount

URL = "https://github.com/astral-sh/uv/releases/download/0.9.9"


def _tar_gz(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for name, contents in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(contents)
            t.addfile(info, io.BytesIO(contents))
    return buf.getvalue()


def _zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, contents in files.items():
            z.writestr(name, contents)
    return buf.getvalue()


def _add_release(archive_name: str, archive: bytes, sha: str | None = None):
    sha = sha or hashlib.sha256(archive).hexdigest()
    responses.add(responses.GET, f"{URL}/{archive_name}", body=archive)
    responses.add(
        responses.GET,
        f"{URL}/{archive_name}.sha256",
        body=f"{sha} *{archive_name}\n",
    )


def test_uv_version_is_installed_version():
    assert bootstrap_uv.uv_version() == importlib.metadata.version("uv")


def test_uv_paths_depend_on_platform():
    assert bootstrap_uv.bootstrap_uv_path("linux", "0.9.9") == "uv/0.9.9/uv"
    assert (
        bootstrap_uv.bootstrap_uv_path("windows", "0.9.9") == "uv/0.9.9/uv.exe"
    )


@responses.activate
def test_can_download_uv_for_linux(tmp_path):
    archive = _tar_gz(
        {
            "uv-x86_64-unknown-linux-gnu/uvx": b"uvx binary",
            "uv-x86_64-unknown-linux-gnu/uv": b"uv binary",
        }
    )
    _add_release("uv-x86_64-unknown-linux-gnu.tar.gz", archive)
    mount = Mount(host="wpia-hn.hpc", remote="hipercow", local=tmp_path)

    bootstrap_uv.bootstrap_uv(mount, "linux", "0.9.9")
    dest = tmp_path / "bootstrap-py-linux/uv/0.9.9/uv"
    assert dest.read_bytes() == b"uv binary"
    if sys.platform != "win32":
        assert os.access(dest, os.X_OK)
    assert [p.name for p in dest.parent.iterdir()] == ["uv"]
    assert len(responses.calls) == 2

    # Already present, so nothing is downloaded
    bootstrap_uv.bootstrap_uv(mount, "linux", "0.9.9")
    assert len(responses.calls) == 2


@responses.activate
def test_can_download_uv_for_windows(tmp_path):
    archive = _zip({"uv.exe": b"uv binary", "uvx.exe": b"uvx binary"})
    _add_release("uv-x86_64-pc-windows-msvc.zip", archive)
    mount = Mount(host="wpia-hn.hpc", remote="hipercow", local=tmp_path)

    bootstrap_uv.bootstrap_uv(mount, "windows", "0.9.9")
    dest = tmp_path / "bootstrap-py-windows/uv/0.9.9/uv.exe"
    assert dest.read_bytes() == b"uv binary"


@responses.activate
def test_refuses_download_with_wrong_checksum(tmp_path):
    archive = _zip({"uv.exe": b"uv binary"})
    _add_release("uv-x86_64-pc-windows-msvc.zip", archive, sha="abc123")
    mount = Mount(host="wpia-hn.hpc", remote="hipercow", local=tmp_path)

    with pytest.raises(Exception, match="but expected abc123"):
        bootstrap_uv.bootstrap_uv(mount, "windows", "0.9.9")
    assert not (tmp_path / "bootstrap-py-windows").exists()


def test_errors_if_archive_does_not_contain_uv():
    archive = _tar_gz({"other/uvx": b"uvx binary"})
    with pytest.raises(Exception, match="Did not find 'uv'"):
        bootstrap_uv._extract(archive, "linux")
