import pytest

from hipercow import root
from hipercow.environment import Empty


def test_empty_env_always_exists(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Empty(r, "empty")
    assert env.exists()


def test_no_path_to_empty_environment(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Empty(r, "empty")
    with pytest.raises(Exception, match="The empty environment has no path"):
        env.path()


def test_cant_provision_empty_environment(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Empty(r, "empty")
    with pytest.raises(Exception, match="Can't create the empty"):
        env.create()
    with pytest.raises(Exception, match="Can't provision the empty"):
        env.provision(None)
