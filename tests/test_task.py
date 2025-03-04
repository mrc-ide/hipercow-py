from unittest import mock

import pytest

from hipercow import root
from hipercow import task_create as tc
from hipercow.task import (
    TaskData,
    TaskStatus,
    TaskTimes,
    TaskWaitWrapper,
    set_task_status,
    task_exists,
    task_info,
    task_list,
    task_log,
    task_status,
    task_wait,
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
        tid = tc.task_create_shell(r, ["echo", "hello world"])
    assert task_exists(r, tid)
    assert task_status(r, tid) == TaskStatus.CREATED
    set_task_status(r, tid, TaskStatus.RUNNING)
    assert task_status(r, tid) == TaskStatus.RUNNING
    set_task_status(r, tid, TaskStatus.SUCCESS)
    assert task_status(r, tid) == TaskStatus.SUCCESS


def test_that_missing_tasks_have_missing_status(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    assert task_status(r, "a" * 32) == TaskStatus.MISSING
    assert not task_exists(r, "a" * 32)


def test_that_missing_tasks_error_on_log_read(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    task_id = "a" * 32
    with pytest.raises(Exception, match="Task '.+' does not exist"):
        task_log(r, task_id)


def test_can_convert_to_nice_string():
    assert str(TaskStatus.CREATED) == "created"


def test_read_task_info(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(r, ["echo", "hello world"])
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
        tid = tc.task_create_shell(r, ["echo", "hello world"])
        task_eval(r, tid)
        info = task_info(r, tid)
    assert info.status == TaskStatus.SUCCESS
    assert info.data == TaskData.read(r, tid)
    assert info.times == TaskTimes.read(r, tid)
    assert isinstance(info.times.created, float)
    assert isinstance(info.times.started, float)
    assert isinstance(info.times.finished, float)


def test_can_list_tasks(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    assert task_list(r) == []
    with transient_working_directory(tmp_path):
        t1 = tc.task_create_shell(r, ["echo", "hello world"])
    assert task_list(r) == [t1]
    with transient_working_directory(tmp_path):
        t2 = tc.task_create_shell(r, ["echo", "hello world"])
    assert set(task_list(r)) == {t1, t2}


def test_can_list_tasks_by_status(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        ids = [tc.task_create_shell(r, ["true"]) for _ in range(5)]
    # 0 is CREATED
    set_task_status(r, ids[1], TaskStatus.RUNNING)
    set_task_status(r, ids[2], TaskStatus.SUCCESS)
    set_task_status(r, ids[3], TaskStatus.SUCCESS)
    set_task_status(r, ids[4], TaskStatus.FAILURE)
    assert set(task_list(r)) == set(ids)
    assert set(task_list(r, with_status=TaskStatus.SUCCESS)) == {ids[2], ids[3]}
    assert set(task_list(r, with_status=TaskStatus.TERMINAL)) == {
        ids[2],
        ids[3],
        ids[4],
    }
    assert set(
        task_list(r, with_status=TaskStatus.SUCCESS | TaskStatus.RUNNING)
    ) == {ids[1], ids[2], ids[3]}


def test_can_wait_on_completed_task(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(r, ["echo", "hello world"])
        task_eval(r, tid)
    assert task_wait(r, tid)


def test_refuse_to_wait_for_created_task(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(r, ["echo", "hello world"])
    with pytest.raises(Exception, match="Cannot wait .+ not been submitted"):
        task_wait(r, tid)


def test_wait_wrapper_can_get_status(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(r, ["echo", "hello world"])
        wrapper = TaskWaitWrapper(r, tid)
        assert wrapper.status() == "created"
        set_task_status(r, tid, TaskStatus.SUCCESS)
        assert wrapper.status() == "success"


def test_wait_wrapper_can_get_log(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(r, ["echo", "hello world"])
        wrapper = TaskWaitWrapper(r, tid)
        assert wrapper.log() is None
        assert wrapper.has_log()
        task_eval(r, tid, capture=True)
        assert wrapper.status() == "success"
        assert wrapper.log() == ["hello world"]
        assert wrapper.has_log()


def test_can_pass_to_task_wait(tmp_path, mocker):
    mock_status = mock.MagicMock(
        side_effect=[TaskStatus.SUBMITTED, TaskStatus.SUCCESS]
    )
    mocker.patch("hipercow.task.task_status", mock_status)
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(r, ["echo", "hello world"])
        assert task_wait(r, tid)
