import pytest

from hipercow import root
from hipercow.environment import (
    EnvironmentConfiguration,
    environment_check,
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
    assert environment_check(r, None) == "default"
    assert environment_check(r, "default") == "default"
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


def test_require_pip_environment_engine(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with pytest.raises(Exception, match="Only the 'pip' and 'empty'"):
        environment_new(r, "default", "conda")
