import os
import platform
from pathlib import Path
from unittest import mock

import pytest

from hipercow.util import (
    check_python_version,
    expand_grid,
    find_file_descend,
    loop_while,
    subprocess_run,
    transient_envvars,
    transient_working_directory,
    truthy_envvar,
)


def test_find_descend(tmp_path):
    (tmp_path / "a" / "b" / "c" / "d").mkdir(parents=True)
    (tmp_path / "a" / "b" / ".foo").mkdir(parents=True)
    assert (
        find_file_descend(".foo", tmp_path / "a/b/c/d")
        == (tmp_path / "a" / "b").resolve()
    )
    assert find_file_descend(".foo", tmp_path / "a") is None


def test_transient_working_directory(tmp_path):
    here = Path.cwd()
    with transient_working_directory(None):
        assert Path.cwd() == here
    with transient_working_directory(tmp_path):
        assert Path.cwd() == tmp_path


def test_run_process_and_capture_output(tmp_path):
    path = tmp_path / "output"
    res = subprocess_run(["echo", "hello"], filename=path)
    assert res.returncode == 0
    assert path.exists()
    with open(path) as f:
        assert f.read().strip() == "hello"


def test_can_cope_with_missing_path(tmp_path, capsys):
    cmd = ["nosuchexe", "arg"]

    res = subprocess_run(cmd)
    assert res.args == cmd
    assert res.returncode == -1
    out = capsys.readouterr()
    assert len(out.out) > 0

    tmp = tmp_path / "log"
    res = subprocess_run(cmd, filename=tmp)
    assert capsys.readouterr().out == ""
    assert res.args == cmd
    assert res.returncode == -1

    with pytest.raises(FileNotFoundError):
        res = subprocess_run(cmd, check=True)


def test_can_set_envvars():
    with transient_envvars({"hc_a": "1"}):
        assert os.environ.get("hc_a") == "1"
    assert os.environ.get("hc_a") is None


def test_can_unset_envvars_if_none():
    with transient_envvars({"hc_a": "1", "hc_b": None, "hc_c": "3"}):
        assert os.environ.get("hc_a") == "1"
        assert "hc_b" not in os.environ
        assert os.environ.get("hc_c") == "3"
        with transient_envvars({"hc_b": "2", "hc_c": None}):
            assert os.environ.get("hc_a") == "1"
            assert os.environ.get("hc_b") == "2"
            assert os.environ.get("hc_c") is None
            assert "hc_c" not in os.environ
        assert os.environ.get("hc_a") == "1"
        assert "hc_b" not in os.environ
        assert os.environ.get("hc_c") == "3"


def test_can_check_python_version():
    ours3 = platform.python_version()
    ours2 = ".".join(ours3.split(".")[:2])
    assert check_python_version(None) == ours2
    assert check_python_version(ours3) == ours2
    assert check_python_version(ours2) == ours2
    assert check_python_version("3.10") == "3.10"
    assert check_python_version("3.11") == "3.11"
    with pytest.raises(Exception, match="does not parse as a valid version"):
        check_python_version("3.11a")
    with pytest.raises(Exception, match="is not supported"):
        check_python_version("3.9")
    assert check_python_version("3.9", ["3.9", "3.10"]) == "3.9"


def test_can_convert_envvar_to_bool():
    with transient_envvars({"hc_a": "1", "hc_b": "true", "hc_c": "TRUE"}):
        assert truthy_envvar("hc_a")
        assert truthy_envvar("hc_b")
        assert truthy_envvar("hc_c")
    with transient_envvars({"hc_a": None, "hc_b": "0", "hc_c": "t"}):
        assert not truthy_envvar("hc_a")
        assert not truthy_envvar("hc_b")
        assert not truthy_envvar("hc_c")


def test_loop_while_loops():
    fn = mock.Mock(side_effect=[True, True, False, False])
    loop_while(fn)
    assert fn.call_count == 3

    fn = mock.Mock(side_effect=[False, True, True, False, False])
    loop_while(fn)
    assert fn.call_count == 1


def test_expand_grid():
    assert expand_grid({}) == [{}]
    assert expand_grid({"a": [1]}) == [{"a": 1}]
    assert expand_grid({"a": [1, 2]}) == [{"a": 1}, {"a": 2}]
    assert expand_grid({"a": [1, 2], "b": [3]}) == [
        {"a": 1, "b": 3},
        {"a": 2, "b": 3},
    ]
    assert expand_grid({"a": [1, 2], "b": [3, 4, 5]}) == [
        {"a": 1, "b": 3},
        {"a": 1, "b": 4},
        {"a": 1, "b": 5},
        {"a": 2, "b": 3},
        {"a": 2, "b": 4},
        {"a": 2, "b": 5},
    ]
