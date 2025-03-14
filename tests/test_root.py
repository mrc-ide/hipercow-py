import shutil

import pytest

from hipercow import root, util


def test_create_root(tmp_path):
    path = tmp_path / "ex"
    root.init(path)
    assert path.exists()
    assert path.is_dir()
    assert (path / "hipercow" / "py").is_dir()
    r = root.open_root(path)
    assert isinstance(r, root.Root)
    assert r.path == path


def test_notify_if_root_exists(tmp_path, capsys):
    path = tmp_path
    root.init(path)
    capsys.readouterr()
    root.init(path)
    captured = capsys.readouterr()
    assert "hipercow already initialised at" in captured.out


def test_notify_if_root_exists_below_requested(tmp_path, capsys):
    path = tmp_path / "a" / "b"
    root.init(tmp_path)
    capsys.readouterr()
    root.init(path)
    captured = capsys.readouterr()
    assert "hipercow already initialised at" in captured.out


def test_error_if_root_invalid(tmp_path):
    (tmp_path / "hipercow").mkdir()
    util.file_create(tmp_path / "hipercow" / "py")
    with pytest.raises(Exception, match="Unexpected file 'hipercow/py'"):
        root.init(tmp_path)


def test_error_if_root_does_not_exist(tmp_path):
    with pytest.raises(Exception, match="Failed to open 'hipercow' root"):
        root.Root(tmp_path)


def test_error_if_non_python_hipercow_root_found(tmp_path):
    root.init(tmp_path)
    shutil.rmtree(tmp_path / "hipercow" / "py")
    pat = "Failed to open non-python 'hipercow' root at"
    with pytest.raises(Exception, match=pat):
        root.Root(tmp_path)


def test_find_root_by_descending(tmp_path):
    path = tmp_path / "a" / "b"
    root.init(tmp_path)
    r = root.open_root(path)
    assert r.path == tmp_path


def test_error_if_no_root_found_by_descending(tmp_path):
    path = tmp_path / "a" / "b"
    with pytest.raises(Exception, match="Failed to find 'hipercow' from"):
        root.open_root(path)


def test_create_gitignore_in_root(tmp_path):
    path = tmp_path / "ex"
    gi = path / "hipercow" / ".gitignore"
    root.init(path)
    assert gi.exists()
    with gi.open() as f:
        assert f.read() == "*\n"


def test_dont_overwrite_existing_gitignore(tmp_path):
    path = tmp_path / "ex"
    gi = path / "hipercow" / ".gitignore"
    (path / "hipercow").mkdir(parents=True)
    with gi.open("w") as f:
        f.write("hello!\n")
    root.init(path)
    assert gi.exists()
    with gi.open() as f:
        assert f.read() == "hello!\n"
