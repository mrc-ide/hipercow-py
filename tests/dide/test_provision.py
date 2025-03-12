from pathlib import Path
from unittest import mock

import hipercow.dide.driver
from hipercow import root
from hipercow.dide import mounts
from hipercow.dide.configuration import DideConfiguration
from hipercow.dide.driver import ProvisionWaitWrapper, _dide_provision
from hipercow.dide.web import DideWebClient
from hipercow.task import TaskStatus
from hipercow.util import transient_working_directory


def test_can_provision_with_dide(tmp_path, mocker):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with (r.path / "requirements.txt").open("w") as f:
        f.write("cowsay\n")

    m = mounts.Mount("host", "hostmount", Path("/local"))
    path_map = mounts.PathMap(tmp_path, m, "Q:", relative="path/to/dir")

    mock_client = mock.MagicMock(spec=DideWebClient)
    mocker.patch("hipercow.dide.driver._web_client", return_value=mock_client)
    mocker.patch("hipercow.dide.driver.taskwait")
    mocker.patch(
        "hipercow.dide.configuration.remap_path", return_value=path_map
    )
    config = DideConfiguration(r, mounts=[m], python_version=None)

    _dide_provision("myenv", "abcdef", config, r)

    assert mock_client.submit.call_count == 1
    assert mock_client.mock_calls[0] == mock.call.submit(
        r"\\host\hostmount\path\to\dir\hipercow\py\env\myenv\provision\abcdef\run.bat",
        "myenv/abcdef",
        template="AllNodes",  # Soon to be "BuildQueue"
    )

    assert hipercow.dide.driver.taskwait.call_count == 1
    assert hipercow.dide.driver.taskwait.mock_calls[0] == mock.call(mock.ANY)
    task = hipercow.dide.driver.taskwait.mock_calls[0].args[0]
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
