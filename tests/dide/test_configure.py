from unittest import mock

from hipercow import root
from hipercow.configure import configure, show_configuration
from hipercow.dide.configuration import DideConfiguration
from hipercow.dide.mounts import Mount
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
    configure("dide", python_version=None, root=r)

    assert list_drivers(r) == ["dide"]
    driver = load_driver("dide", r)
    assert driver.config == DideConfiguration(
        r, mounts=mock_mounts, python_version=None
    )


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
    configure("dide", python_version=None, root=r)
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


def test_provision_using_driver(tmp_path, mocker):
    path = tmp_path / "a" / "b"
    root.init(path)
    r = root.open_root(path)
    mock_mounts = [Mount("projects", "other", tmp_path)]
    mock_provision = mock.MagicMock()
    mocker.patch("hipercow.dide.driver.detect_mounts", return_value=mock_mounts)
    mocker.patch("hipercow.dide.driver._dide_provision", mock_provision)
    configure("dide", python_version=None, root=r)
    environment_new("default", "pip", r)
    provision("default", [], root=r)
    cfg = load_driver(None, r).config
    assert mock_provision.call_count == 1
    assert mock_provision.mock_calls[0] == mock.call(
        "default", mock.ANY, cfg, r
    )


def test_configure_python_version(tmp_path, mocker, capsys):
    path = tmp_path / "a" / "b"
    root.init(path)
    r = root.open_root(path)
    mock_mounts = [Mount("projects", "other", tmp_path)]
    mocker.patch("hipercow.dide.driver.detect_mounts", return_value=mock_mounts)
    configure("dide", python_version="3.12", root=r)
    capsys.readouterr()
    show_configuration(None, r)
    out = capsys.readouterr().out
    assert (
        out
        == """Configuration for 'dide'
path mapping:
  drive: V:
  share: \\\\projects\\other
python version: 3.12
"""
    )
