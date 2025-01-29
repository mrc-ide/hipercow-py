import pytest

from hipercow import root
from hipercow import task_create as tc
from hipercow.task import (
    TaskData,
    TaskStatus,
    TaskTimes,
    set_task_status,
    task_info,
    task_log,
    task_status,
)
from hipercow.task_eval import task_eval
from hipercow.util import transient_working_directory


def test_can_check_if_tasks_are_runnable():
    assert TaskStatus.CREATED.is_runnable()
    assert not TaskStatus.CREATED.is_terminal()

    assert not TaskStatus.RUNNING.is_runnable()
    assert not TaskStatus.RUNNING.is_terminal()

    assert not TaskStatus.SUCCESS.is_runnable()
    assert TaskStatus.SUCCESS.is_terminal()


def test_can_set_task_status(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["echo", "hello world"])
    assert task_status(r, tid) == TaskStatus.CREATED
    set_task_status(r, tid, TaskStatus.RUNNING)
    assert task_status(r, tid) == TaskStatus.RUNNING
    set_task_status(r, tid, TaskStatus.SUCCESS)
    assert task_status(r, tid) == TaskStatus.SUCCESS


def test_that_missing_tasks_have_missing_status(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    assert task_status(r, "a" * 32) == TaskStatus.MISSING


def test_that_missing_tasks_error_on_log_read(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    task_id = "a" * 32
    with pytest.raises(Exception, match="Task log for '.+' does not exist"):
        task_log(r, task_id)


def test_can_convert_to_nice_string():
    assert str(TaskStatus.CREATED) == "created"


def test_read_task_info(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["echo", "hello world"])
    info = task_info(r, tid)
    assert info.status == TaskStatus.CREATED
    assert info.data == TaskData.read(r, tid)
    assert info.times == TaskTimes.read(r, tid)
    assert isinstance(info.times.created, float)
    assert info.times.started is None
    assert info.times.finished is None


def test_that_missing_tasks_error_on_task_info(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    task_id = "a" * 32
    with pytest.raises(Exception, match="Task '.+' does not exist"):
        task_info(r, task_id)


def test_that_can_read_info_for_completed_task(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["echo", "hello world"])
        task_eval(r, tid)
        info = task_info(r, tid)
    assert info.status == TaskStatus.SUCCESS
    assert info.data == TaskData.read(r, tid)
    assert info.times == TaskTimes.read(r, tid)
    assert isinstance(info.times.created, float)
    assert isinstance(info.times.started, float)
    assert isinstance(info.times.finished, float)
