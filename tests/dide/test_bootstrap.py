from pathlib import Path
from unittest import mock

import pytest

from hipercow.dide.bootstrap import (
    BootstrapTask,
    _bootstrap_args,
    _bootstrap_check_pipx_pyz,
    _bootstrap_mount,
    _bootstrap_python_versions,
    _bootstrap_submit,
    _bootstrap_target,
    _bootstrap_unc,
    _bootstrap_wait,
    bootstrap,
)
from hipercow.dide.mounts import Mount
from hipercow.dide.web import DideWebClient
from hipercow.resources import TaskResources
from hipercow.util import file_create


def test_can_construct_unc_paths():
    assert _bootstrap_unc(Path("a/b")) == r"\\wpia-hn\hipercow\a\b"


def test_can_build_args():
    assert _bootstrap_args(force=False, verbose=False) == ""
    assert _bootstrap_args(force=True, verbose=False) == "--force"
    assert _bootstrap_args(force=False, verbose=True) == "--verbose"
    assert _bootstrap_args(force=True, verbose=True) == "--force --verbose"


def test_can_detect_bootstrap_mount():
    mounts = [
        Mount(host="foo", remote="path", local=Path("a")),
        Mount(host="bar", remote="hipercow", local=Path("b")),
        Mount(host="wpia-hn.hpc", remote="hipercow", local=Path("c")),
    ]
    assert _bootstrap_mount(mounts) == mounts[2]
    with pytest.raises(Exception, match="Failed to find"):
        _bootstrap_mount(mounts[:1])


def test_can_use_pypi_hipercow():
    assert _bootstrap_target(None, None, "abcdef") == "hipercow"


def test_can_use_local_hipercow(tmp_path):
    src = tmp_path / "src"
    mount = Mount(host="wpia-hn.hpc", remote="hipercow", local=tmp_path / "dst")
    with pytest.raises(FileNotFoundError):
        _bootstrap_target(str(src), mount, "abcdef")
    with src.open("w") as f:
        f.write("contents\n")
    res = _bootstrap_target(str(src), mount, "abcdef")
    assert res == r"\\wpia-hn\hipercow\bootstrap-py-windows\in\abcdef\src"
    dst = tmp_path / "dst/bootstrap-py-windows/in/abcdef/src"
    assert dst.exists()
    with dst.open() as f:
        assert f.read() == "contents\n"


def test_can_submit_bootstrap_task(tmp_path):
    client = mock.MagicMock(spec=DideWebClient)
    mount = Mount(host="wpia-hn.hpc", remote="hipercow", local=tmp_path)
    bootstrap_id = "abcdef"
    version = "3.11"
    target = "hipercow"
    args = ""
    platform = "windows"
    t = _bootstrap_submit(
        client, mount, bootstrap_id, version, platform, target, args
    )
    resources = TaskResources(queue="AllNodes")
    assert t.client == client
    assert client.submit.call_count == 1
    assert client.submit.mock_calls[0] == mock.call(
        r"\\wpia-hn\hipercow\bootstrap-py-windows\in\abcdef\3.11.bat",
        "bootstrap/abcdef/3.11",
        resources,
    )
    assert t.dide_id == client.submit.return_value
    dest = tmp_path / "bootstrap-py-windows/in/abcdef/3.11.bat"
    assert dest.exists()
    with dest.open() as f:
        contents = f.readlines()
    assert "call set_python_311_64\n" in contents

    assert t.log() is None
    assert not t.has_log()

    status = t.status()
    assert client.status_job.call_count == 1
    assert client.status_job.mock_calls[0] == mock.call(t.dide_id)
    assert status == str(client.status_job.return_value)


def test_can_wait_on_successful_tasks(tmp_path, capsys):
    client = mock.MagicMock(spec=DideWebClient)
    client.status_job.return_value = "success"
    mount = Mount(host="wpia-hn.hpc", remote="hipercow", local=tmp_path)
    bootstrap_id = "abcdef"
    tasks = [
        BootstrapTask(mount, bootstrap_id, client, "1", "3.11", "windows"),
        BootstrapTask(mount, bootstrap_id, client, "2", "3.12", "windows"),
    ]
    _bootstrap_wait(tasks)
    out = capsys.readouterr().out
    assert "Waiting on 2 tasks" in out
    assert "3.11: success" in out
    assert "3.12: success" in out


def test_can_error_on_failed_tasks(tmp_path, capsys):
    client = mock.MagicMock(spec=DideWebClient)
    client.status_job.side_effect = ["success", "failure"]
    client.log.return_value = "some log"
    mount = Mount(host="wpia-hn.hpc", remote="hipercow", local=tmp_path)
    bootstrap_id = "abcdef"
    tasks = [
        BootstrapTask(mount, bootstrap_id, client, "1011", "3.11", "windows"),
        BootstrapTask(mount, bootstrap_id, client, "1012", "3.12", "windows"),
    ]
    tasks[1].path_log.parent.mkdir(parents=True)
    with tasks[1].path_log.open("w") as f:
        f.write("log1\nlog2\n")
    with pytest.raises(Exception, match="1/2 bootstrap tasks failed"):
        _bootstrap_wait(tasks)
    out = capsys.readouterr().out
    assert "3.11: success" in out
    assert "3.12: failure" in out
    assert "Additional logs from cluster for task '1012':" in out
    assert "\nsome log\n" in out
    assert "Logs from pipx:" in out
    assert "\nlog1\nlog2\n" in out


# This test is revolting:
def test_can_launch_bootstrap(mocker):
    mock_client = mock.MagicMock(spec=DideWebClient)
    mock_mount = mock.MagicMock()
    mock_submit = mock.MagicMock()
    mock_wait = mock.MagicMock()
    mock_rmtree = mock.MagicMock()

    mocker.patch("hipercow.dide.bootstrap._web_client", mock_client)
    mocker.patch("hipercow.dide.bootstrap._bootstrap_mount", mock_mount)
    mocker.patch("hipercow.dide.bootstrap._bootstrap_submit", mock_submit)
    mocker.patch("hipercow.dide.bootstrap._bootstrap_wait", mock_wait)
    mocker.patch("shutil.rmtree", mock_rmtree)
    bootstrap(None)

    assert mock_client.call_count == 1
    assert mock_mount.call_count == 1
    assert mock_submit.call_count == 8

    client = mock_client.return_value
    mount = mock_mount.return_value

    assert mock_submit.mock_calls[0] == mock.call(
        client, mount, mock.ANY, "3.10", "windows", "hipercow", ""
    )
    assert mock_wait.call_count == 1
    assert len(mock_wait.mock_calls[0].args[0]) == 8
    assert mock_wait.mock_calls[0].args[0][3] == mock_submit.return_value


def test_error_if_no_pipx_pyz(tmp_path):
    with pytest.raises(Exception, match="Expected 'pipx.pyz' to be found"):
        _bootstrap_check_pipx_pyz(tmp_path)
    file_create(tmp_path / "pipx.pyz")
    assert _bootstrap_check_pipx_pyz(tmp_path) is None


def test_can_set_versions_to_install():
    assert _bootstrap_python_versions(["3.13"]) == ["3.13"]
    assert _bootstrap_python_versions(None) == ["3.10", "3.11", "3.12", "3.13"]
