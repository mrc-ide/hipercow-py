from pathlib import Path
from subprocess import CompletedProcess
from unittest import mock

import pytest

from hipercow.dide import mounts


def test_can_parse_cifs_output():
    m = mounts._parse_unix_mount_entry(
        "//projects/other on /path/local type cifs (rw,relatime)"
    )
    assert m == mounts.Mount(
        host="projects", remote="other", local=Path("/path/local")
    )


def test_can_parse_mounts_on_unix(mocker):
    data = b"""//projects/other on /path/local type cifs (rw,relatime)
//projects/other2 on /path/local2 type cifs (rw,relatime)"""
    response = mock.MagicMock(spec=CompletedProcess)
    response.stdout = data
    mocker.patch("subprocess.run", return_value=response)
    res = mounts._detect_mounts_unix("Linux")
    assert len(res) == 2
    assert res[0] == mounts.Mount(
        host="projects", remote="other", local=Path("/path/local")
    )
    assert res[1] == mounts.Mount(
        host="projects", remote="other2", local=Path("/path/local2")
    )


def test_can_clean_dide_hostname():
    assert mounts._clean_dide_hostname("qdrive") == "qdrive"
    assert mounts._clean_dide_hostname("qdrive.dide.ic.ac.uk") == "qdrive"
    assert mounts._clean_dide_hostname("qdrive.other") == "qdrive.other"


def test_can_parse_mounts_on_windows(mocker):
    data = b"""#TYPE Microsoft.Management.Infrastructure.CimInstance#ROOT/Microsoft/Windows/SMB/MSFT_SmbMapping
"Status","LocalPath","RemotePath","RequireIntegrity","RequirePrivacy","UseWriteThrough","PSComputerName"
"OK","I:","\\\\wpia-hn\\hipercow","False","False","False",
"OK","Y:","\\\\wpia-hn2.hpc.dide.ic.ac.uk\\Climate","False","False","False",
"Disconnected","Z:","\\\\wpia-hn\\all-wpia-hn","False","False","False","""  # noqa: E501
    response = mock.MagicMock(spec=CompletedProcess)
    response.stdout = data
    mocker.patch("subprocess.run", return_value=response)
    res = mounts._detect_mounts_windows()
    assert len(res) == 2
    assert res[0] == mounts.Mount(
        host="wpia-hn", remote="hipercow", local=Path("I:/")
    )
    assert res[1] == mounts.Mount(
        host="wpia-hn2.hpc", remote="Climate", local=Path("Y:/")
    )


def test_can_get_correct_smb_type():
    assert mounts._unix_smb_mount_type("Linux") == "cifs"
    assert mounts._unix_smb_mount_type("Darwin") == "smbfs"


def test_throw_on_remap_with_no_mounts():
    with pytest.raises(Exception, match="Can't map local directory"):
        mounts.remap_path(Path.cwd(), [])


def test_can_remap_path():
    m = [mounts.Mount(host="host", remote="/hostmount", local=Path("/local"))]
    path = Path("/local/path/to/dir")
    res = mounts.remap_path(path, m)
    assert res == mounts.PathMap(
        path=path, mount=m[0], remote="V:", relative="path/to/dir"
    )


def test_throw_if_two_plausible_mounts():
    m = [
        mounts.Mount(host="host1", remote="/path1", local=Path("/local/path")),
        mounts.Mount(host="host2", remote="/path2", local=Path("/local")),
    ]
    path = Path("/local/path/to/dir")
    with pytest.raises(Exception, match="More than one plausible"):
        mounts.remap_path(path, m)


def test_preserve_drive_letter_if_given():
    m = [mounts.Mount(host="host", remote="/hostmount", local=Path("P:/"))]
    path = Path("P:/local/path")
    res = mounts.remap_path(path, m)
    assert res == mounts.PathMap(
        path=path, mount=m[0], remote="P:", relative="local/path"
    )


def test_can_map_home_to_q_drive():
    m = [mounts.Mount(host="qdrive", remote="user", local=Path("/local"))]
    path = Path("/local/path/to/dir")
    res = mounts.remap_path(path, m)
    assert res == mounts.PathMap(
        path=path, mount=m[0], remote="Q:", relative="path/to/dir"
    )


def test_can_parse_unix_entry():
    res = mounts._parse_unix_mount_entry(
        "//projects.dide.ic.ac.uk/other on /path/local type cifs (rw,relatime)"
    )
    assert res == mounts.Mount(
        host="projects", remote="other", local=Path("/path/local")
    )


def test_throw_if_error_in_unix_mount_entry():
    with pytest.raises(Exception, match="Failed to match mount output"):
        mounts._parse_unix_mount_entry("")


def test_can_parse_windows_mount_point():
    res = mounts._parse_windows_mount_entry(
        "E:", "//projects.dide.ic.ac.uk/other"
    )
    assert res == mounts.Mount(
        host="projects", remote="other", local=Path("E:/")
    )


def test_throw_if_error_in_windows_mount_point():
    with pytest.raises(Exception, match="Failed to parse windows entry"):
        mounts._parse_windows_mount_entry("", "E:")


def test_use_windows_detection_on_windows(mocker):
    mock_detect_windows = mock.Mock()
    mock_detect_unix = mock.Mock()
    mocker.patch("platform.system", return_value="Windows")
    mocker.patch(
        "hipercow.dide.mounts._detect_mounts_windows", mock_detect_windows
    )
    mocker.patch("hipercow.dide.mounts._detect_mounts_unix", mock_detect_unix)
    mounts.detect_mounts()
    assert mock_detect_windows.call_count == 1
    assert mock_detect_unix.call_count == 0


def test_use_windows_detection_on_unix(mocker):
    mock_detect_windows = mock.Mock()
    mock_detect_unix = mock.Mock()
    mocker.patch("platform.system", return_value="Linux")
    mocker.patch(
        "hipercow.dide.mounts._detect_mounts_windows", mock_detect_windows
    )
    mocker.patch("hipercow.dide.mounts._detect_mounts_unix", mock_detect_unix)
    mounts.detect_mounts()
    assert mock_detect_windows.call_count == 0
    assert mock_detect_unix.call_count == 1
