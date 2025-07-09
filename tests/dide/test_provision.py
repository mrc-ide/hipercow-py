from pathlib import Path
from unittest import mock

import pytest
from taskwait import Result

import hipercow.dide.driver
from hipercow import root
from hipercow.dide import mounts
from hipercow.dide.batch_windows import _dide_provision_win
from hipercow.dide.configuration import dide_configuration
from hipercow.dide.provision import ProvisionWaitWrapper
from hipercow.dide.web import DideWebClient
from hipercow.resources import TaskResources
from hipercow.task import TaskStatus
from hipercow.util import transient_working_directory


def test_can_provision_with_dide_win(tmp_path, mocker):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with (r.path / "requirements.txt").open("w") as f:
        f.write("cowsay\n")

    m = mounts.Mount(host="host", remote="hostmount", local=Path("/local"))
    path_map = mounts.PathMap(
        path=tmp_path, mount=m, remote="Q:", relative="path/to/dir"
    )

    mock_client = mock.MagicMock(spec=DideWebClient)
    mocker.patch("hipercow.dide.batch_windows.taskwait")
    mocker.patch(
        "hipercow.dide.configuration.remap_path", return_value=path_map
    )
    config = dide_configuration(
        r, mounts=[m], python_version=None, check_credentials=False
    )

    _dide_provision_win("myenv", "abcdef", config, mock_client, r)
    resources = TaskResources(queue="BuildQueue")

    assert mock_client.submit.call_count == 1
    assert mock_client.mock_calls[0] == mock.call.submit(
        r"\\host\hostmount\path\to\dir\hipercow\py\env\myenv\provision\abcdef\run.bat",
        "myenv/abcdef",
        resources=resources,
    )

    assert hipercow.dide.batch_windows.taskwait.call_count == 1
    assert hipercow.dide.batch_windows.taskwait.mock_calls[0] == mock.call(
        mock.ANY
    )
    task = hipercow.dide.batch_windows.taskwait.mock_calls[0].args[0]
    assert isinstance(task, ProvisionWaitWrapper)
    assert task.client == mock_client
    assert task.dide_id == mock_client.submit.return_value


def test_can_get_status_from_wait_wrapper():
    client = mock.MagicMock(spec=DideWebClient)
    client.status_job.side_effect = [TaskStatus.RUNNING, TaskStatus.SUCCESS]
    task = ProvisionWaitWrapper(mock.ANY, "myenv", "abcdef", client, "1234")
    assert task.status() == "running"
    assert task.status() == "success"
    assert client.status_job.call_count == 2


def test_wait_wrapper_can_get_log(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        name = "myenv"
        provision_id = "abcdef"
        task = ProvisionWaitWrapper(r, name, provision_id, mock.ANY, "1234")
        r.path_provision(name, provision_id).mkdir(parents=True)
        assert task.log() is None
        assert task.has_log()
        with r.path_provision_log(name, provision_id).open("w") as f:
            f.write("a\nb\n")
        assert task.log() == ["a", "b"]
        assert task.has_log()


def test_throw_after_failed_provision_with_dide_win(tmp_path, mocker, capsys):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with (r.path / "requirements.txt").open("w") as f:
        f.write("cowsay\n")

    m = mounts.Mount(host="host", remote="hostmount", local=Path("/local"))
    path_map = mounts.PathMap(
        path=tmp_path, mount=m, remote="Q:", relative="path/to/dir"
    )

    mock_client = mock.MagicMock(spec=DideWebClient)
    mock_client.log.return_value = "more logs"
    result = Result("failure", 100, 123)
    mocker.patch("hipercow.dide.batch_windows.taskwait", return_value=result)
    mocker.patch(
        "hipercow.dide.configuration.remap_path", return_value=path_map
    )
    config = dide_configuration(
        r, mounts=[m], python_version=None, check_credentials=False
    )

    capsys.readouterr()
    with pytest.raises(Exception, match="Provisioning failed"):
        _dide_provision_win("myenv", "abcdef", config, mock_client, r)
    out = capsys.readouterr().out

    assert "Provisioning failed after 23s!\n" in out
    assert "\nmore logs\n" in out

    assert mock_client.submit.call_count == 1
    assert mock_client.log.call_count == 1
    assert mock_client.log.mock_calls[0] == mock.call(
        mock_client.submit.return_value
    )
    assert hipercow.dide.batch_windows.taskwait.call_count == 1
