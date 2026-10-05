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
    environment_new("default", "pip", r)
    assert environment_list(r) == ["default", "empty"]
    with pytest.raises(Exception, match="'default' already exists"):
        environment_new("default", "pip", r)
    with r.path_environment_config("default").open() as f:
        cfg = EnvironmentConfiguration.model_validate_json(f.read())
    assert cfg.engine == "pip"


def test_environment_selection(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    assert environment_check("empty", r) == "empty"
    assert environment_check(None, r) == "empty"
    with pytest.raises(Exception, match="No such environment 'default'"):
        environment_check("default", r)
    with pytest.raises(Exception, match="No such environment 'other'"):
        environment_check("other", r)

    environment_new("default", "pip", r)
    assert environment_check("empty", r) == "empty"
    assert environment_check(None, r) == "default"
    assert environment_check("default", r) == "default"
    with pytest.raises(Exception, match="No such environment 'other'"):
        environment_check("other", r)

    environment_new("other", "pip", r)
    assert environment_check("empty", r) == "empty"
    assert environment_check(None, r) == "default"
    assert environment_check("default", r) == "default"
    assert environment_check("other", r) == "other"
    with pytest.raises(Exception, match="No such environment 'other2'"):
        environment_check("other2", r)


def test_delete_environment(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)

    environment_new("default", "pip", r)
    environment_new("other", "pip", r)

    assert environment_list(r) == ["default", "empty", "other"]
    assert environment_exists("other", r)

    environment_delete("other", r)
    assert environment_list(r) == ["default", "empty"]
    assert not environment_exists("other", r)

    environment_delete("default", r)
    assert environment_list(r) == ["empty"]
    assert not environment_exists("default", r)

    with pytest.raises(Exception, match="Can't delete the empty environment"):
        environment_delete("empty", r)


def test_can_only_delete_non_empty_default_environment(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with pytest.raises(Exception, match="as it is empty"):
        environment_delete("default", r)


def test_cant_delete_unknown_environment(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with pytest.raises(Exception, match="as it does not exist"):
        environment_delete("other", r)


def test_require_known_environment_engine(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with pytest.raises(
        Exception, match="Only the 'uv', 'pip', 'conda' and 'empty'"
    ):
        environment_new("default", "renv", r)


def test_create_conda_environment(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    environment_new("default", "conda", r)
    assert environment_list(r) == ["default", "empty"]
    with r.path_environment_config("default").open() as f:
        cfg = EnvironmentConfiguration.model_validate_json(f.read())
    assert cfg.engine == "conda"


def test_create_uv_environment(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    environment_new("default", "uv", r)
    environment_new("other", "uv", r, python="3.13")
    assert environment_list(r) == ["default", "empty", "other"]
    with r.path_environment_config("default").open() as f:
        cfg = EnvironmentConfiguration.model_validate_json(f.read())
    assert cfg.engine == "uv"
    assert cfg.python is None
    with r.path_environment_config("other").open() as f:
        cfg = EnvironmentConfiguration.model_validate_json(f.read())
    assert cfg.engine == "uv"
    assert cfg.python == "3.13"


def test_python_version_only_written_when_given(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    environment_new("default", "pip", r)
    with r.path_environment_config("default").open() as f:
        assert f.read() == '{"engine":"pip"}'


def test_python_version_requires_uv_engine(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    for engine in ["pip", "conda", "empty"]:
        with pytest.raises(Exception, match="only supported by the 'uv'"):
            environment_new("default", engine, r, python="3.12")
    assert environment_list(r) == ["empty"]
