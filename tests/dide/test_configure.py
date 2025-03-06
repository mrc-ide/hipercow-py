from unittest import mock

from hipercow import root
from hipercow.configure import configure, show_configuration
from hipercow.dide.driver import DideConfiguration
from hipercow.dide.mounts import Mount, remap_path
from hipercow.dide.web import Credentials, DideWebClient
from hipercow.driver import list_drivers, load_driver
from hipercow.environment import environment_new
from hipercow.provision import provision
from hipercow.task_create import task_create_shell
from hipercow.util import transient_working_directory


def test_can_configure_dide_mount(tmp_path, mocker):
    path = tmp_path / "a" / "b"
    root.init(path)
    r = root.open_root(path)
    mock_mounts = [Mount("projects", "other", tmp_path)]
    mocker.patch("hipercow.dide.driver.detect_mounts", return_value=mock_mounts)
    configure(r, "dide")

    assert list_drivers(r) == ["dide"]
    driver = load_driver(r, "dide")
    path_map = remap_path(path, mock_mounts)
    assert driver.config == DideConfiguration(path_map)


def test_creating_task_triggers_submission(tmp_path, mocker):
    path = tmp_path / "a" / "b"
    root.init(path)
    r = root.open_root(path)
    mock_mounts = [Mount("projects", "other", tmp_path)]
    mock_creds = Credentials("bob", "secret")
    mock_web_client = mock.MagicMock(spec=DideWebClient)
    mocker.patch("hipercow.dide.driver.detect_mounts", return_value=mock_mounts)
    mocker.patch(
        "hipercow.dide.driver.fetch_credentials", return_value=mock_creds
    )
    mocker.patch("hipercow.dide.driver.DideWebClient", mock_web_client)
    configure(r, "dide")
    with transient_working_directory(path):
        tid = task_create_shell(r, ["echo", "hello world"])

    assert mock_web_client.call_count == 1
    assert mock_web_client.call_args == mock.call(mock_creds)
    cl = mock_web_client.return_value
    assert cl.login.call_count == 1
    assert cl.submit.call_count == 1
    # testing arguments here would be possibly useful, but we hit
    # issues with pathname normalisation very quickly.
    assert (r.path_task(tid) / "task_run.bat").exists()


def test_provision_using_driver(tmp_path, mocker):
    path = tmp_path / "a" / "b"
    root.init(path)
    r = root.open_root(path)
    mock_mounts = [Mount("projects", "other", tmp_path)]
    mock_provision = mock.MagicMock()
    path_map = remap_path(path, mock_mounts)
    mocker.patch("hipercow.dide.driver.detect_mounts", return_value=mock_mounts)
    mocker.patch("hipercow.dide.driver._dide_provision", mock_provision)
    configure(r, "dide")
    environment_new(r, "default", "pip")
    provision(r, "default", [])
    assert mock_provision.call_count == 1
    assert mock_provision.mock_calls[0] == mock.call(
        r, "default", mock.ANY, path_map
    )


def test_configure_python_version(tmp_path, mocker, capsys):
    path = tmp_path / "a" / "b"
    root.init(path)
    r = root.open_root(path)
    mock_mounts = [Mount("projects", "other", tmp_path)]
    mocker.patch("hipercow.dide.driver.detect_mounts", return_value=mock_mounts)
    configure(r, "dide", python_version="3.12")
    capsys.readouterr()
    show_configuration(r)
    out = capsys.readouterr().out
    assert out == """Configuration for 'dide'
path mapping:
  drive: V:
  share: \\\\projects\\other
python version: 3.12
"""
