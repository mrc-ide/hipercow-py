from subprocess import CompletedProcess
from unittest import mock

from hipercow.dide import mounts


def test_can_parse_cifs_output():
    m = mounts._parse_unix_mount_entry(
        "//projects/other on /path/local type cifs (rw,relatime)"
    )
    assert m == mounts.Mount("projects", "other", "/path/local")


def test_can_parse_mounts_on_unix(mocker):
    data = b"""//projects/other on /path/local type cifs (rw,relatime)
//projects/other2 on /path/local2 type cifs (rw,relatime)"""
    response = mock.MagicMock(spec=CompletedProcess)
    response.stdout = data
    mocker.patch("subprocess.run", return_value=response)
    res = mounts._detect_mounts_unix()
    assert len(res) == 2
    assert res[0] == Mount("projects", "other", "/path/local")
    assert res[1] == Mount("projects", "other2", "/path/local2")
