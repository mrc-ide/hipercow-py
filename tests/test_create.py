import re

import pytest

from hipercow import root
from hipercow import task_create as tc
from hipercow.configure import configure
from hipercow.resources import TaskResources
from hipercow.task import TaskData, TaskStatus, task_data_read, task_status
from hipercow.util import transient_working_directory


def test_create_simple_task(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["echo", "hello world"], root=r)
    assert re.match("^[0-9a-f]{32}$", tid)
    path_data = (
        tmp_path / "hipercow" / "py" / "tasks" / tid[:2] / tid[2:] / "data"
    )
    assert path_data.exists()
    d = task_data_read(tid, root.open_root(tmp_path))
    assert isinstance(d, TaskData)
    assert d.task_id == tid
    assert d.method == "shell"
    assert d.data == {"cmd": ["echo", "hello world"]}
    assert d.path == "."
    assert d.envvars == {}
    assert d.resources is None


def test_tasks_cannot_be_empty(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with pytest.raises(Exception, match="cannot be empty"):
        with transient_working_directory(tmp_path):
            tc.task_create_shell([], root=r)


def test_submit_with_driver_if_configured(tmp_path, capsys):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    configure("example", root=r)
    capsys.readouterr()
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["echo", "hello world"], root=r)
    str1 = capsys.readouterr().out
    assert f"submitting '{tid}'" in str1
    assert task_status(tid, r) == TaskStatus.SUBMITTED


def test_resources_require_configured_driver(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    resources = TaskResources(queue="foo")
    with transient_working_directory(tmp_path):
        with pytest.raises(Exception, match="Can't specify resources"):
            tc.task_create_shell(
                ["echo", "hello world"], resources=resources, root=r
            )


def test_resources_validated_on_submission(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    configure("example", root=r)
    resources = TaskResources(queue="foo")
    with transient_working_directory(tmp_path):
        with pytest.raises(
            Exception, match="Queue 'foo' is not in valid queue list"
        ):
            tc.task_create_shell(
                ["echo", "hello world"], resources=resources, root=r
            )


def test_can_save_resources_on_submission(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    configure("example", root=r)
    resources = TaskResources(memory_per_task=1)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(
            ["echo", "hello world"], resources=resources, root=r
        )
    d = task_data_read(tid, root.open_root(tmp_path))
    assert d.resources == TaskResources(queue="default", memory_per_task=1)
