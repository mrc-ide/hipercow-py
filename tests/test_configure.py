import pytest

from hipercow import root
from hipercow.configure import configure, unconfigure
from hipercow.example import ExampleDriver


def test_no_drivers_are_available_by_default(tmp_path):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    assert r.list_drivers() == []
    assert r.load_driver(None, allow_none=True) is None
    with pytest.raises(Exception, match="No driver configured"):
        r.load_driver(None)
    with pytest.raises(Exception, match="No such configuration 'example'"):
        r.load_driver("example")


def test_can_configure_driver(tmp_path):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    configure(r, "example")
    assert r.list_drivers() == ["example"]
    assert isinstance(r.load_driver(None), ExampleDriver)


def test_can_unconfigure_driver(tmp_path):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    configure(r, "example")
    assert r.list_drivers() == ["example"]
    unconfigure(r, "example")
    assert r.list_drivers() == []
    unconfigure(r, "example")
    assert r.list_drivers() == []


def test_throw_if_unknown_driver(tmp_path):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    with pytest.raises(Exception, match="No such driver 'other'"):
        configure(r, "other")


def test_can_reconfigure_driver(tmp_path, capsys):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    capsys.readouterr()
    configure(r, "example")
    str1 = capsys.readouterr().out
    assert str1.startswith("Configured hipercow to use 'example'")
    configure(r, "example")
    str2 = capsys.readouterr().out
    assert str2.startswith("Updated configuration for 'example'")
