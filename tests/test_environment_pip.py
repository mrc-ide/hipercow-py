import os
from unittest import mock

import pytest

from hipercow import root
from hipercow.environment import environment_engine, environment_new
from hipercow.environment_engines import Pip
from hipercow.util import file_create, transient_working_directory


def test_pip_environment_does_not_exist_until_created(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Pip(r, "default")
    assert not env.exists()
    env.path().mkdir(parents=True)
    assert env.exists()


def test_pip_environment_can_be_created(tmp_path, mocker):
    mock_run = mock.MagicMock()
    mocker.patch("subprocess.run", mock_run)

    root.init(tmp_path)
    file_create(tmp_path / "requirements.txt")
    r = root.open_root(tmp_path)
    environment_new("default", "pip", r)
    env = environment_engine("default", r)
    assert isinstance(env, Pip)

    venv_path = str(env.path())
    envvars = env._envvars()

    env.create()
    assert mock_run.call_count == 1
    assert mock_run.mock_calls[0] == mock.call(
        ["python", "-m", "venv", venv_path], check=True, env=os.environ
    )

    with transient_working_directory(tmp_path):
        cmd = env.check_args(None)
        assert cmd == ["pip", "install", "--verbose", "-r", "requirements.txt"]
        env.provision(cmd)
        assert mock_run.call_count == 2
        assert mock_run.mock_calls[1] == mock.call(
            cmd,
            env=os.environ | envvars,
            check=True,
        )


def test_pip_can_determine_sensible_default_cmd(tmp_path):
    root.init(tmp_path)
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Pip(r, "default")

    with transient_working_directory(tmp_path):
        with pytest.raises(Exception, match="Can't determine install"):
            env._auto()
        file_create(tmp_path / "requirements.txt")
        assert env._auto() == [
            "pip",
            "install",
            "--verbose",
            "-r",
            "requirements.txt",
        ]
        file_create(tmp_path / "pyproject.toml")
        assert env._auto() == ["pip", "install", "--verbose", "."]

        assert env.check_args(None) == ["pip", "install", "--verbose", "."]
        assert env.check_args([]) == ["pip", "install", "--verbose", "."]
        assert env.check_args(["pip", "install", "x"]) == [
            "pip",
            "install",
            "x",
        ]
        with pytest.raises(Exception, match="Expected first element"):
            assert env.check_args(["pwd"])
