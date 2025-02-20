from unittest import mock

import pytest

from hipercow import root
from hipercow.configure import configure
from hipercow.environment import (
    Pip,
    Platform,
    environment_create,
    environment_list,
    environment_provision,
)


def test_create_pip_environment(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    assert environment_list(r) == []
    environment_create(r, "default", "pip")
    assert environment_list(r) == ["default"]


def test_throw_on_provision_if_no_driver(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    environment_create(r, "default", "pip")
    with pytest.raises(Exception, match="Can't provision, no driver"):
        environment_provision(r, "default", [])


def test_provision_with_example_driver(tmp_path, mocker):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with (r.path / "requirements.txt").open("w") as f:
        f.write("cowsay\n")
    configure(r, "example")
    mock_run = mock.MagicMock()
    mocker.patch("subprocess.run", mock_run)
    environment_create(r, "default", "pip")
    environment_provision(r, "default", [])

    pr = Pip(r, Platform.local(), "default")
    venv_path = str(pr.path())
    env = pr._envvars()

    assert mock_run.call_count == 2
    assert mock_run.mock_calls[0] == mock.call(
        ["python", "-m", "venv", venv_path], check=True
    )
    assert mock_run.mock_calls[1] == mock.call(
        ["pip", "install", "--verbose", "-r", "requirements.txt"],
        env=env,
        check=True,
    )
