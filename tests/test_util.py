from pathlib import Path

from hipercow.util import find_file_descend, transient_working_directory


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
