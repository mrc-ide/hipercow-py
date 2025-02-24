from unittest import mock

import pytest

from hipercow import root
from hipercow.environment_engines import Empty
from hipercow.environment import environment_engine


def test_empty_environment_has_no_path_but_always_exists(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Empty(r, "empty")

    assert env.exists()
    with pytest.raises(Exception, match="The empty environment has no path"):
        env.path()


def test_can_load_empty_engine(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    assert isinstance(environment_engine(r, "empty"), Empty)
    assert isinstance(environment_engine(r, "default"), Empty)


def test_empty_environment_cannot_be_created(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Empty(r, "empty")
    with pytest.raises(Exception, match="Can't create the empty environment!"):
        env.create()


def test_empty_environment_cannot_be_provisioned(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Empty(r, "empty")
    with pytest.raises(Exception, match="Can't provision the empty"):
        env.provision([])


def test_can_run_command_in_empty_env(tmp_path, mocker):
    mock_run = mock.MagicMock()
    mocker.patch("subprocess.run", mock_run)
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Empty(r, "empty")
    env.run(["some", "command"])
    assert mock_run.call_count == 1
    assert mock_run.mock_calls[0] == mock.call(
        ["some", "command"], env=None, check=False
    )
