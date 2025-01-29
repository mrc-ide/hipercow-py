from pathlib import Path

from hipercow.util import (
    find_file_descend,
    subprocess_run,
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
