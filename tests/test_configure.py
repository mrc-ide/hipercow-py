import pytest

from hipercow import root
from hipercow.configure import (
    _write_configuration,
    configure,
    unconfigure,
)
from hipercow.driver import (
    list_drivers,
    load_driver,
    load_driver_optional,
    show_configuration,
)
from hipercow.example import ExampleDriver, ExampleDriverConfiguration
from hipercow.task import TaskStatus, task_log, task_status
from hipercow.task_create import task_create_shell
from hipercow.task_eval import task_eval
from hipercow.util import transient_working_directory


def test_no_drivers_are_available_by_default(tmp_path):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    assert list_drivers(r) == []
    assert load_driver_optional(None, r) is None
    with pytest.raises(Exception, match="No driver configured"):
        load_driver(None, r)
    with pytest.raises(Exception, match="No such driver 'example'"):
        load_driver("example", r)


def test_can_configure_driver(tmp_path):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    configure("example", root=r)
    assert list_drivers(r) == ["example"]
    assert isinstance(load_driver(None, r), ExampleDriver)


def test_can_unconfigure_driver(tmp_path):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    configure("example", root=r)
    assert list_drivers(r) == ["example"]
    unconfigure("example", r)
    assert list_drivers(r) == []
    unconfigure("example", r)
    assert list_drivers(r) == []


def test_throw_if_unknown_driver(tmp_path):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    with pytest.raises(Exception, match="No such driver 'other'"):
        configure("other", root=r)


def test_can_reconfigure_driver(tmp_path, capsys):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    capsys.readouterr()
    configure("example", root=r)
    str1 = capsys.readouterr().out
    assert "Configured hipercow to use 'example'" in str1
    configure("example", root=r)
    str2 = capsys.readouterr().out
    assert "Updated configuration for 'example'" in str2


def test_get_default_driver(tmp_path):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    a = ExampleDriverConfiguration()
    b = ExampleDriverConfiguration()
    _write_configuration("a", a, r)
    _write_configuration("b", b, r)
    with pytest.raises(Exception, match="More than one candidate driver"):
        load_driver(None, r)


def test_can_show_configuration(tmp_path, capsys):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    configure("example", root=r)
    capsys.readouterr()
    capsys.readouterr()
    show_configuration(None, r)
    out = capsys.readouterr().out
    assert "Configuration for 'example'" in out
    assert "(no configuration)" in out


def test_can_read_logs_with_example_driver(tmp_path):
    path = tmp_path / "ex"
    root.init(path)
    r = root.open_root(path)
    configure("example", root=r)
    with transient_working_directory(path):
        tid = task_create_shell(["echo", "hello world"], root=r)
    assert task_status(tid, root=r) == TaskStatus.SUBMITTED
    dr = load_driver("example", r)
    assert dr.task_log(tid, root=r) is None
    assert dr.task_log(tid, outer=True, root=r) is None
    with transient_working_directory(path):
        task_eval(tid, capture=True, root=r)
    assert dr.task_log(tid, root=r) == "hello world\n"
    assert dr.task_log(tid, outer=True, root=r) is None
    assert task_log(tid, root=r) == "hello world\n"
    assert task_log(tid, outer=True, root=r) is None


def test_that_example_driver_has_reasonable_resources(tmp_path):
    dr = ExampleDriver(root.init(tmp_path))
    resources = dr.resources()
    assert resources.queues.valid == {"default"}
    assert resources.max_cores == 1
    assert resources.max_memory == 32
