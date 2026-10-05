import re
from pathlib import Path
from unittest import mock

import pytest

from hipercow.dide.bootstrap import (
    BootstrapTask,
    _bootstrap_install_name,
    _bootstrap_mount,
    _bootstrap_platforms,
    _bootstrap_prepare,
    _bootstrap_submit,
    _bootstrap_wait,
    bootstrap,
)
from hipercow.dide.bootstrap_install import RE_NAME
from hipercow.dide.mounts import Mount
from hipercow.dide.web import DideWebClient
from hipercow.resources import TaskResources


def test_can_detect_bootstrap_mount():
    mounts = [
        Mount(host="foo", remote="path", local=Path("a")),
        Mount(host="bar", remote="hipercow", local=Path("b")),
        Mount(host="wpia-hn.hpc", remote="hipercow", local=Path("c")),
    ]
    assert _bootstrap_mount(mounts) == mounts[2]
    with pytest.raises(Exception, match="Failed to find"):
        _bootstrap_mount(mounts[:1])


def test_install_name_is_valid():
    name = _bootstrap_install_name("abcdef12")
    assert RE_NAME.match(name)
    assert name.endswith("-abcdef12")


def test_can_prepare_bootstrap_from_pypi(tmp_path):
    mount = Mount(host="wpia-hn.hpc", remote="hipercow", local=tmp_path)
    assert _bootstrap_prepare(mount, "abcdef", "linux", None) is None
    dest = tmp_path / "bootstrap-py-linux/in/abcdef"
    assert [p.name for p in dest.iterdir()] == ["bootstrap_install.py"]


def test_can_prepare_bootstrap_from_file(tmp_path):
    src = tmp_path / "hipercow-1.2.3-py3-none-any.whl"
    with src.open("w") as f:
        f.write("contents\n")
    mount = Mount(host="wpia-hn.hpc", remote="hipercow", local=tmp_path / "dst")
    res = _bootstrap_prepare(mount, "abcdef", "windows", str(src))
    assert res == "hipercow-1.2.3-py3-none-any.whl"
    dest = tmp_path / "dst/bootstrap-py-windows/in/abcdef"
    assert (dest / "bootstrap_install.py").exists()
    with (dest / res).open() as f:
        assert f.read() == "contents\n"


def test_can_submit_windows_bootstrap_task(tmp_path):
    client = mock.MagicMock(spec=DideWebClient)
    mount = Mount(host="wpia-hn.hpc", remote="hipercow", local=tmp_path)
    t = _bootstrap_submit(
        client, mount, "abcdef", "name", "3.11", "windows", None, "", "0.9.9"
    )
    resources = TaskResources(queue="AllNodes")
    assert t.client == client
    assert client.submit.call_count == 1
    assert client.submit.mock_calls[0] == mock.call(
        r"\\wpia-hn\hipercow\bootstrap-py-windows\in\abcdef\3.11.bat",
        "bootstrap/abcdef/windows/3.11",
        resources,
    )
    assert t.dide_id == client.submit.return_value
    assert t.path_log == tmp_path / "bootstrap-py-windows/in/abcdef/3.11.log"
    dest = tmp_path / "bootstrap-py-windows/in/abcdef/3.11.bat"
    assert dest.exists()
    with dest.open() as f:
        contents = f.readlines()
    assert not any("set_python" in x for x in contents)
    assert "set UV_MANAGED_PYTHON=1\n" in contents
    root = r"\\wpia-hn-app\hipercow\bootstrap-py-windows"
    uv = rf"{root}\uv\0.9.9\uv.exe"
    cmd = (
        rf"{uv} run --no-project --python 3.11 "
        rf"{root}\in\abcdef\bootstrap_install.py --root {root} "
        f"--python-version 3.11 --name name --uv {uv}  hipercow > "
        rf"{root}\in\abcdef\3.11.log 2>&1" + "\n"
    )
    assert cmd in contents

    assert t.log() is None
    assert not t.has_log()

    status = t.status()
    assert client.status_job.call_count == 1
    assert client.status_job.mock_calls[0] == mock.call(t.dide_id)
    assert status == str(client.status_job.return_value)


def test_can_submit_linux_bootstrap_task(tmp_path):
    client = mock.MagicMock(spec=DideWebClient)
    mount = Mount(host="wpia-hn.hpc", remote="hipercow", local=tmp_path)
    t = _bootstrap_submit(
        client,
        mount,
        "abcdef",
        "name",
        "3.11",
        "linux",
        "x.whl",
        "--verbose",
        "0.9.9",
    )
    resources = TaskResources(queue="LinuxNodes")
    assert client.submit.call_count == 1
    assert client.submit.mock_calls[0] == mock.call(
        "/mnt/cluster/Hipercow/bootstrap-py-linux/in/abcdef/3.11.sh",
        "bootstrap/abcdef/linux/3.11",
        resources,
    )
    assert t.path_log == tmp_path / "bootstrap-py-linux/in/abcdef/3.11.log"
    dest = tmp_path / "bootstrap-py-linux/in/abcdef/3.11.sh"
    with dest.open(newline="") as f:
        contents = f.read()
    assert "\r" not in contents
    assert "module" not in contents
    assert "export UV_MANAGED_PYTHON=1\n" in contents
    root = "/mnt/cluster/Hipercow/bootstrap-py-linux"
    path_in = f"{root}/in/abcdef"
    uv = f"{root}/uv/0.9.9/uv"
    assert (
        f"{uv} run --no-project --python 3.11 {path_in}/bootstrap_install.py "
        f"--root {root} --python-version 3.11 --name name --uv {uv} "
        f"--verbose {path_in}/x.whl > {path_in}/3.11.log 2>&1\n"
    ) in contents


def test_cant_submit_bootstrap_to_unknown_platform(tmp_path):
    client = mock.MagicMock(spec=DideWebClient)
    mount = Mount(host="wpia-hn.hpc", remote="hipercow", local=tmp_path)
    with pytest.raises(ValueError, match="Unsupported platform 'macos'"):
        _bootstrap_submit(
            client, mount, "abcdef", "name", "3.11", "macos", None, "", "0.9.9"
        )
    assert client.submit.call_count == 0


def test_can_wait_on_successful_tasks(tmp_path, capsys):
    client = mock.MagicMock(spec=DideWebClient)
    client.status_job.return_value = "success"
    mount = Mount(host="wpia-hn.hpc", remote="hipercow", local=tmp_path)
    bootstrap_id = "abcdef"
    tasks = [
        BootstrapTask(mount, bootstrap_id, client, "1", "3.11", "windows"),
        BootstrapTask(mount, bootstrap_id, client, "2", "3.12", "linux"),
    ]
    _bootstrap_wait(tasks)
    out = capsys.readouterr().out
    assert "Waiting on 2 tasks" in out
    assert "windows 3.11: success" in out
    assert "linux 3.12: success" in out


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
    assert "windows 3.11: success" in out
    assert "windows 3.12: failure" in out
    assert "Additional logs from cluster for task '1012':" in out
    assert "\nsome log\n" in out
    assert "Logs from bootstrap:" in out
    assert "\nlog1\nlog2\n" in out


# This test is revolting:
def test_can_launch_bootstrap(mocker):
    mock_client = mock.MagicMock(spec=DideWebClient)
    mock_mount = mock.MagicMock()
    mock_prepare = mock.MagicMock(return_value=None)
    mock_submit = mock.MagicMock()
    mock_wait = mock.MagicMock()
    mock_uv = mock.MagicMock()

    mocker.patch("hipercow.dide.bootstrap._web_client", mock_client)
    mocker.patch("hipercow.dide.bootstrap.bootstrap_uv", mock_uv)
    mocker.patch("hipercow.dide.bootstrap.uv_version", return_value="0.9.9")
    mocker.patch("hipercow.dide.bootstrap._bootstrap_mount", mock_mount)
    mocker.patch("hipercow.dide.bootstrap._bootstrap_prepare", mock_prepare)
    mocker.patch("hipercow.dide.bootstrap._bootstrap_submit", mock_submit)
    mocker.patch("hipercow.dide.bootstrap._bootstrap_wait", mock_wait)
    bootstrap(None)

    assert mock_client.call_count == 1
    assert mock_mount.call_count == 1
    assert mock_prepare.call_count == 2
    assert mock_submit.call_count == 8

    client = mock_client.return_value
    mount = mock_mount.return_value

    assert mock_uv.mock_calls == [
        mock.call(mount, "windows", "0.9.9"),
        mock.call(mount, "linux", "0.9.9"),
    ]
    assert mock_prepare.mock_calls[0] == mock.call(
        mount, mock.ANY, "windows", None
    )
    assert mock_prepare.mock_calls[1] == mock.call(
        mount, mock.ANY, "linux", None
    )
    assert mock_submit.mock_calls[0] == mock.call(
        client, mount, mock.ANY, mock.ANY, "3.10", "windows", None, "", "0.9.9"
    )
    assert mock_submit.mock_calls[4] == mock.call(
        client, mount, mock.ANY, mock.ANY, "3.10", "linux", None, "", "0.9.9"
    )
    # All tasks share a single installation name
    names = {c.args[3] for c in mock_submit.mock_calls}
    assert len(names) == 1
    assert re.match(r"^[0-9]{14}-[0-9a-f]{8}$", names.pop())
    assert mock_wait.call_count == 1
    assert len(mock_wait.mock_calls[0].args[0]) == 8
    assert mock_wait.mock_calls[0].args[0][3] == mock_submit.return_value


def test_bootstrap_errors_early_if_target_missing(mocker, tmp_path):
    mock_client = mock.MagicMock(spec=DideWebClient)
    mocker.patch("hipercow.dide.bootstrap._web_client", mock_client)
    with pytest.raises(FileNotFoundError, match="does not exist"):
        bootstrap(str(tmp_path / "hipercow.whl"))
    assert mock_client.call_count == 0


def test_can_set_platforms_to_install():
    assert _bootstrap_platforms(None) == ["windows", "linux"]
    assert _bootstrap_platforms(["linux"]) == ["linux"]
    with pytest.raises(ValueError, match="Unsupported platform 'macos'"):
        _bootstrap_platforms(["linux", "macos"])
