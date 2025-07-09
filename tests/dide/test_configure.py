from unittest import mock

from hipercow import root
from hipercow.configure import configure
from hipercow.dide.configuration import dide_configuration
from hipercow.dide.mounts import Mount
from hipercow.dide.web import Credentials, DideWebClient
from hipercow.driver import list_drivers, load_driver, show_configuration
from hipercow.environment import environment_new
from hipercow.provision import provision
from hipercow.resources import TaskResources
from hipercow.task import task_log
from hipercow.task_create import task_create_shell
from hipercow.util import file_create, transient_working_directory


def test_can_configure_dide_mount(tmp_path, mocker):
    path = tmp_path / "a" / "b"
    root.init(path)
    r = root.open_root(path)
    mock_mounts = [Mount(host="projects", remote="other", local=tmp_path)]
    mock_check_auth = mock.Mock()
    mocker.patch("hipercow.dide.driver.detect_mounts", return_value=mock_mounts)
    mocker.patch("hipercow.dide.configuration.check_auth", mock_check_auth)
    configure("dide-windows", python_version=None, root=r)

    assert list_drivers(r) == ["dide-windows"]
    assert mock_check_auth.call_count == 1
    assert mock_check_auth.mock_calls[0] == mock.call()

    driver = load_driver("dide-windows", r)
    assert driver.config == dide_configuration(
        r, mounts=mock_mounts, python_version=None, check_credentials=False
    )


def test_creating_task_triggers_submission(tmp_path, mocker):
    path = tmp_path / "a" / "b"
    root.init(path)
    r = root.open_root(path)
    mock_mounts = [Mount(host="projects", remote="other", local=tmp_path)]
    mock_creds = Credentials("bob", "secret")
    mock_web_client = mock.MagicMock(spec=DideWebClient)

    mocker.patch("hipercow.dide.driver.detect_mounts", return_value=mock_mounts)
    mocker.patch(
        "hipercow.dide.driver.fetch_credentials", return_value=mock_creds
    )
    mocker.patch("hipercow.dide.driver.DideWebClient", mock_web_client)
    mock_web_client.return_value.submit.return_value = "1234"

    configure(
        "dide-windows", python_version=None, root=r, check_credentials=False
    )
    with transient_working_directory(path):
        tid = task_create_shell(["echo", "hello world"], root=r)

    assert mock_web_client.call_count == 1
    assert mock_web_client.call_args == mock.call(mock_creds)
    cl = mock_web_client.return_value
    assert cl.login.call_count == 1
    assert cl.submit.call_count == 1
    # testing arguments here would be possibly useful, but we hit
    # issues with pathname normalisation very quickly.
    assert (r.path_task(tid) / "task_run.bat").exists()


def test_creating_task_with_resources(tmp_path, mocker):
    path = tmp_path / "a" / "b"
    root.init(path)
    r = root.open_root(path)
    mock_mounts = [Mount(host="projects", remote="other", local=tmp_path)]
    mock_creds = Credentials("bob", "secret")
    mock_web_client = mock.MagicMock(spec=DideWebClient)

    mocker.patch("hipercow.dide.driver.detect_mounts", return_value=mock_mounts)
    mocker.patch(
        "hipercow.dide.driver.fetch_credentials", return_value=mock_creds
    )
    mocker.patch("hipercow.dide.driver.DideWebClient", mock_web_client)
    mock_web_client.return_value.submit.return_value = "1234"

    configure(
        "dide-windows", python_version=None, check_credentials=False, root=r
    )
    resources = TaskResources(cores=4)
    with transient_working_directory(path):
        tid = task_create_shell(
            ["echo", "hello world"], resources=resources, root=r
        )

    assert mock_web_client.call_count == 1
    assert mock_web_client.call_args == mock.call(mock_creds)
    cl = mock_web_client.return_value
    assert cl.login.call_count == 1
    assert cl.submit.call_count == 1
    assert cl.submit.mock_calls[0][2]["resources"] == TaskResources(
        queue="AllNodes", cores=4
    )
    assert (r.path_task(tid) / "task_run.bat").exists()


def test_provision_using_driver(tmp_path, mocker):
    path = tmp_path / "a" / "b"
    root.init(path)
    r = root.open_root(path)
    mock_mounts = [Mount(host="projects", remote="other", local=tmp_path)]
    mock_provision = mock.MagicMock()
    mocker.patch("hipercow.dide.driver.detect_mounts", return_value=mock_mounts)
    mocker.patch("hipercow.dide.driver._web_client", return_value=mock.Mock())
    mocker.patch("hipercow.dide.driver._dide_provision_win", mock_provision)
    configure(
        "dide-windows", python_version=None, check_credentials=False, root=r
    )
    environment_new("default", "pip", r)
    file_create(r.path / "requirements.txt")
    provision("default", [], root=r)
    cfg = load_driver(None, r).config
    assert mock_provision.call_count == 1
    assert mock_provision.mock_calls[0] == mock.call(
        "default", mock.ANY, cfg, mock.ANY, r
    )


def test_resources_using_driver(tmp_path, mocker):
    path = tmp_path / "a" / "b"
    root.init(path)
    r = root.open_root(path)
    mock_mounts = [Mount(host="projects", remote="other", local=tmp_path)]
    mock_provision = mock.MagicMock()
    mocker.patch("hipercow.dide.driver.detect_mounts", return_value=mock_mounts)
    mocker.patch("hipercow.dide.driver._dide_provision_win", mock_provision)
    configure(
        "dide-windows", python_version=None, check_credentials=False, root=r
    )
    dr = load_driver(None, r)
    resources = dr.resources()
    assert resources.queues.default == "AllNodes"
    assert resources.max_cores == 32
    assert resources.max_memory == 512


def test_configure_python_version(tmp_path, mocker, capsys):
    path = tmp_path / "a" / "b"
    root.init(path)
    r = root.open_root(path)
    mock_mounts = [Mount(host="projects", remote="other", local=tmp_path)]
    mocker.patch("hipercow.dide.driver.detect_mounts", return_value=mock_mounts)
    configure(
        "dide-windows", python_version="3.12", check_credentials=False, root=r
    )
    capsys.readouterr()
    show_configuration(None, r)
    out = capsys.readouterr().out
    assert "Python version: 3.12" in out


def test_get_outer_logs_from_web_client(tmp_path, mocker):
    path = tmp_path / "a" / "b"
    root.init(path)
    r = root.open_root(path)
    mock_mounts = [Mount(host="projects", remote="other", local=tmp_path)]
    mock_creds = Credentials("bob", "secret")
    mock_web_client = mock.MagicMock(spec=DideWebClient)
    mocker.patch("hipercow.dide.driver.detect_mounts", return_value=mock_mounts)
    mocker.patch(
        "hipercow.dide.driver.fetch_credentials", return_value=mock_creds
    )
    mocker.patch(
        "hipercow.dide.driver.DideWebClient", return_value=mock_web_client
    )
    mock_web_client.submit.return_value = "1234"
    configure(
        "dide-windows", python_version=None, check_credentials=False, root=r
    )
    with transient_working_directory(path):
        tid = task_create_shell(["echo", "hello world"], root=r)

    assert task_log(tid, root=r) is None
    assert mock_web_client.log.call_count == 0

    res = task_log(tid, outer=True, root=r)
    assert res == mock_web_client.log.return_value
    assert mock_web_client.log.call_count == 1
    assert mock_web_client.log.mock_calls[0] == mock.call("1234")
