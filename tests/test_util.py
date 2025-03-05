import os
from pathlib import Path

import pytest

from hipercow.util import (
    find_file_descend,
    subprocess_run,
    transient_envvars,
    transient_working_directory,
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
