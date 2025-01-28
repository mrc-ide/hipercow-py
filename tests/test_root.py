import pytest

from hipercow import root, util


def test_create_root(tmp_path):
    path = tmp_path / "ex"
    root.init(path)
    assert path.exists()
    assert path.is_dir()
    assert (path / "hipercow" / "py").exists()
    r = root.open_root(path)
    assert isinstance(r, root.Root)
    assert r.path == path


def test_notify_if_root_exists(tmp_path, capsys):
    path = tmp_path
    root.init(path)
    capsys.readouterr()
    root.init(path)
    captured = capsys.readouterr()
    assert captured.out.startswith("hipercow already initialised at")


def test_notify_if_root_exists_below_requested(tmp_path, capsys):
    path = tmp_path / "a" / "b"
    root.init(tmp_path)
    capsys.readouterr()
    root.init(path)
    captured = capsys.readouterr()
    assert captured.out.startswith("hipercow already initialised at")


def test_error_if_root_invalid(tmp_path):
    util.file_create(tmp_path / "hipercow")
    with pytest.raises(Exception, match="Unexpected file 'hipercow'"):
        root.init(tmp_path)


def test_error_if_root_does_not_exist(tmp_path):
    with pytest.raises(Exception, match="Failed to open 'hipercow' root"):
        root.Root(tmp_path)


def test_error_if_non_python_hipercow_root_found(tmp_path):
    root.init(tmp_path)
    (tmp_path / "hipercow" / "py").unlink()
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
