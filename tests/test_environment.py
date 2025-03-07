import pytest

from hipercow import root
from hipercow.environment import (
    EnvironmentConfiguration,
    environment_check,
    environment_delete,
    environment_exists,
    environment_list,
    environment_new,
)


def test_create_pip_environment(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    assert environment_list(r) == ["empty"]
    environment_new(r, "default", "pip")
    assert environment_list(r) == ["default", "empty"]
    with pytest.raises(Exception, match="'default' already exists"):
        environment_new(r, "default", "pip")
    cfg = EnvironmentConfiguration.read(r, "default")
    assert cfg.engine == "pip"


def test_environment_selection(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    assert environment_check(r, "empty") == "empty"
    assert environment_check(r, None) == "empty"
    with pytest.raises(Exception, match="No such environment 'default'"):
        environment_check(r, "default")
    with pytest.raises(Exception, match="No such environment 'other'"):
        environment_check(r, "other")

    environment_new(r, "default", "pip")
    assert environment_check(r, "empty") == "empty"
    assert environment_check(r, None) == "default"
    assert environment_check(r, "default") == "default"
    with pytest.raises(Exception, match="No such environment 'other'"):
        environment_check(r, "other")

    environment_new(r, "other", "pip")
    assert environment_check(r, "empty") == "empty"
    assert environment_check(r, None) == "default"
    assert environment_check(r, "default") == "default"
    assert environment_check(r, "other") == "other"
    with pytest.raises(Exception, match="No such environment 'other2'"):
        environment_check(r, "other2")


def test_delete_environment(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)

    environment_new(r, "default", "pip")
    environment_new(r, "other", "pip")

    assert environment_list(r) == ["default", "empty", "other"]
    assert environment_exists(r, "other")

    environment_delete(r, "other")
    assert environment_list(r) == ["default", "empty"]
    assert not environment_exists(r, "other")

    environment_delete(r, "default")
    assert environment_list(r) == ["empty"]
    assert not environment_exists(r, "default")

    with pytest.raises(Exception, match="Can't delete the empty environment"):
        environment_delete(r, "empty")


def test_can_only_delete_non_empty_default_environment(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with pytest.raises(Exception, match="as it is empty"):
        environment_delete(r, "default")


def test_cant_delete_unknown_environment(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with pytest.raises(Exception, match="as it does not exist"):
        environment_delete(r, "other")


def test_require_pip_environment_engine(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with pytest.raises(Exception, match="Only the 'pip' and 'empty'"):
        environment_new(r, "default", "conda")
