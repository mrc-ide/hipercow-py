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
    configure("example", root=r)
    mock_run = mock.MagicMock()
    mocker.patch("subprocess.run", mock_run)
    environment_new("default", "pip", r)
    provision("default", [], root=r)

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

    h = provision_history("default", r)
    assert len(h) == 1
    assert h[0].result.error is None

    id = h[0].data.id
    with pytest.raises(Exception, match="has already been run"):
        provision_run("default", id, r)

    r.path_provision_result("default", id).unlink()
    h2 = provision_history("default", r)
    assert len(h) == 1
    assert h2[0].result is None


def test_dont_create_on_second_provision(tmp_path, mocker):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    file_create(r.path / "pyproject.toml")
    configure("example", root=r)
    mock_run = mock.MagicMock()
    mocker.patch("subprocess.run", mock_run)

    environment_new("default", "pip", r)
    pr = Pip(r, "default")
    pr.path().mkdir(parents=True)

    provision("default", [], root=r)
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
    configure("example", root=r)
    mock_run = mock.MagicMock(side_effect=Exception("some ghastly error"))
    mocker.patch("subprocess.run", mock_run)

    environment_new("default", "pip", r)
    pr = Pip(r, "default")
    pr.path().mkdir(parents=True)

    with pytest.raises(Exception, match="Provisioning failed"):
        provision("default", [], root=r)
    assert mock_run.call_count == 1

    assert mock_run.mock_calls[0] == mock.call(
        ["pip", "install", "--verbose", "."],
        env=os.environ | pr._envvars(),
        check=True,
        stderr=mock.ANY,
        stdout=mock.ANY,
    )

    h = provision_history("default", r)
    assert len(h) == 1
    assert h[0].result.error == "some ghastly error"


def test_throw_on_provision_if_no_environment(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    configure("example", root=r)
    with pytest.raises(Exception, match="Environment 'default' does not exist"):
        provision("default", [], root=r)
