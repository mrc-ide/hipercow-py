import pytest

from hipercow import root
from hipercow.configure import _write_configuration, configure, unconfigure
from hipercow.driver import list_drivers, load_driver, load_driver_optional
from hipercow.example import ExampleDriver


def test_no_drivers_are_available_by_default(tmp_path):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    assert list_drivers(r) == []
    assert load_driver_optional(r, None) is None
    with pytest.raises(Exception, match="No driver configured"):
        load_driver(r, None)
    with pytest.raises(Exception, match="No such driver 'example'"):
        load_driver(r, "example")


def test_can_configure_driver(tmp_path):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    configure(r, "example")
    assert list_drivers(r) == ["example"]
    assert isinstance(load_driver(r, None), ExampleDriver)


def test_can_unconfigure_driver(tmp_path):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    configure(r, "example")
    assert list_drivers(r) == ["example"]
    unconfigure(r, "example")
    assert list_drivers(r) == []
    unconfigure(r, "example")
    assert list_drivers(r) == []


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


def test_get_default_driver(tmp_path):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    a = ExampleDriver(r)
    a.name = "a"
    b = ExampleDriver(r)
    b.name = "b"
    _write_configuration(r, a)
    _write_configuration(r, b)
    with pytest.raises(Exception, match="More than one candidate driver"):
        load_driver(r, None)
