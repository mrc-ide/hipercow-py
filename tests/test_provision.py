import os
from unittest import mock

import pytest

from hipercow import root
from hipercow.configure import configure
from hipercow.environment import environment_new
from hipercow.environment_engines import Pip
from hipercow.provision import provision, provision_history, provision_run
from hipercow.util import file_create


def test_provision_with_example_driver(tmp_path, mocker):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with (r.path / "requirements.txt").open("w") as f:
        f.write("cowsay\n")
    configure(r, "example")
    mock_run = mock.MagicMock()
    mocker.patch("subprocess.run", mock_run)
    environment_new("default", "pip", r)
    provision(r, "default", [])

    pr = Pip(r, "default")
    venv_path = str(pr.path())
    env = pr._envvars()

    assert mock_run.call_count == 2
    assert mock_run.mock_calls[0] == mock.call(
        ["python", "-m", "venv", venv_path],
        env=os.environ,
        check=True,
        stderr=mock.ANY,
        stdout=mock.ANY,
    )
    assert mock_run.mock_calls[1] == mock.call(
        ["pip", "install", "--verbose", "-r", "requirements.txt"],
        env=os.environ | env,
        check=True,
        stderr=mock.ANY,
        stdout=mock.ANY,
    )

    h = provision_history(r, "default")
    assert len(h) == 1
    assert h[0].result.error is None

    id = h[0].data.id
    with pytest.raises(Exception, match="has already been run"):
        provision_run(r, "default", id)

    r.path_provision_result("default", id).unlink()
    h2 = provision_history(r, "default")
    assert len(h) == 1
    assert h2[0].result is None


def test_dont_create_on_second_provision(tmp_path, mocker):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    file_create(r.path / "pyproject.toml")
    configure(r, "example")
    mock_run = mock.MagicMock()
    mocker.patch("subprocess.run", mock_run)

    environment_new("default", "pip", r)
    pr = Pip(r, "default")
    pr.path().mkdir(parents=True)

    provision(r, "default", [])
    assert mock_run.call_count == 1

    assert mock_run.mock_calls[0] == mock.call(
        ["pip", "install", "--verbose", "."],
        env=os.environ | pr._envvars(),
        check=True,
        stderr=mock.ANY,
        stdout=mock.ANY,
    )


def test_record_provisioning_error(tmp_path, mocker):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    file_create(r.path / "pyproject.toml")
    configure(r, "example")
    mock_run = mock.MagicMock(side_effect=Exception("some ghastly error"))
    mocker.patch("subprocess.run", mock_run)

    environment_new("default", "pip", r)
    pr = Pip(r, "default")
    pr.path().mkdir(parents=True)

    with pytest.raises(Exception, match="Provisioning failed"):
        provision(r, "default", [])
    assert mock_run.call_count == 1

    assert mock_run.mock_calls[0] == mock.call(
        ["pip", "install", "--verbose", "."],
        env=os.environ | pr._envvars(),
        check=True,
        stderr=mock.ANY,
        stdout=mock.ANY,
    )

    h = provision_history(r, "default")
    assert len(h) == 1
    assert isinstance(h[0].result.error, Exception)


def test_throw_on_provision_if_no_environment(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    configure(r, "example")
    with pytest.raises(Exception, match="Environment 'default' does not exist"):
        provision(r, "default", [])
