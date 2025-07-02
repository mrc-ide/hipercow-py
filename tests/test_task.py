import time
from unittest import mock

import pytest

from hipercow import root
from hipercow import task_create as tc
from hipercow.task import (
    TaskStatus,
    TaskWaitWrapper,
    _read_task_times,
    check_task_id,
    is_valid_task_id,
    set_task_status,
    task_data_read,
    task_driver,
    task_exists,
    task_info,
    task_last,
    task_list,
    task_log,
    task_recent,
    task_recent_rebuild,
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
        tid = tc.task_create_shell(["echo", "hello world"], root=r)
    assert task_exists(tid, r)
    assert task_status(tid, r) == TaskStatus.CREATED
    set_task_status(tid, TaskStatus.RUNNING, None, r)
    assert task_status(tid, r) == TaskStatus.RUNNING
    set_task_status(tid, TaskStatus.SUCCESS, None, r)
    assert task_status(tid, r) == TaskStatus.SUCCESS


def test_that_missing_tasks_have_missing_status(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    assert task_status("a" * 32, r) == TaskStatus.MISSING
    assert not task_exists("a" * 32, r)


def test_that_missing_tasks_error_on_log_read(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    task_id = "a" * 32
    with pytest.raises(Exception, match="Task '.+' does not exist"):
        task_log(task_id, root=r)


def test_can_convert_to_nice_string():
    assert str(TaskStatus.CREATED) == "created"


def test_read_task_info(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["echo", "hello world"], root=r)
    info = task_info(tid, r)
    assert info.status == TaskStatus.CREATED
    assert info.data == task_data_read(tid, r)
    assert info.times == _read_task_times(tid, r)
    assert isinstance(info.times.created, float)
    assert info.times.started is None
    assert info.times.finished is None


def test_that_missing_tasks_error_on_task_info(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    task_id = "a" * 32
    with pytest.raises(Exception, match="Task '.+' does not exist"):
        task_info(task_id, r)


def test_that_can_read_info_for_completed_task(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["echo", "hello world"], root=r)
        task_eval(tid, capture=False, root=r)
        info = task_info(tid, r)
    assert info.status == TaskStatus.SUCCESS
    assert info.data == task_data_read(tid, r)
    assert info.times == _read_task_times(tid, r)
    assert isinstance(info.times.created, float)
    assert isinstance(info.times.started, float)
    assert isinstance(info.times.finished, float)


def test_can_list_tasks(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    assert task_list(root=r) == []
    with transient_working_directory(tmp_path):
        t1 = tc.task_create_shell(["echo", "hello world"], root=r)
    assert task_list(root=r) == [t1]
    with transient_working_directory(tmp_path):
        t2 = tc.task_create_shell(["echo", "hello world"], root=r)
    assert set(task_list(root=r)) == {t1, t2}


def test_can_list_tasks_by_status(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        ids = [tc.task_create_shell(["true"], root=r) for _ in range(5)]
    # 0 is CREATED
    set_task_status(ids[1], TaskStatus.RUNNING, None, r)
    set_task_status(ids[2], TaskStatus.SUCCESS, None, r)
    set_task_status(ids[3], TaskStatus.SUCCESS, None, r)
    set_task_status(ids[4], TaskStatus.FAILURE, None, r)
    assert set(task_list(root=r)) == set(ids)
    assert set(task_list(root=r, with_status=TaskStatus.SUCCESS)) == {
        ids[2],
        ids[3],
    }
    assert set(task_list(root=r, with_status=TaskStatus.TERMINAL)) == {
        ids[2],
        ids[3],
        ids[4],
    }
    assert set(
        task_list(root=r, with_status=TaskStatus.SUCCESS | TaskStatus.RUNNING)
    ) == {ids[1], ids[2], ids[3]}


def test_can_wait_on_completed_task(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["echo", "hello world"], root=r)
        task_eval(tid, capture=False, root=r)
    assert task_wait(tid, root=r)


def test_refuse_to_wait_for_created_task(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["echo", "hello world"], root=r)
    with pytest.raises(Exception, match="Cannot wait .+ not been submitted"):
        task_wait(tid, root=r)


def test_wait_wrapper_can_get_status(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["echo", "hello world"], root=r)
        wrapper = TaskWaitWrapper(tid, r)
        assert wrapper.status() == "created"
        set_task_status(tid, TaskStatus.SUCCESS, None, r)
        assert wrapper.status() == "success"


def test_wait_wrapper_can_get_log(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["echo", "hello world"], root=r)
        wrapper = TaskWaitWrapper(tid, r)
        assert wrapper.log() is None
        assert wrapper.has_log()
        task_eval(tid, capture=True, root=r)
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
        tid = tc.task_create_shell(["echo", "hello world"], root=r)
        assert task_wait(tid, root=r)


def test_can_get_last_task_when_none_are_created(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    assert task_last(r) is None
    assert task_recent(root=r) == []


# This might not work wonderfully on windows, because the timing there
# tends to be too coarse.
def test_can_get_recent_tasks(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        ids = [
            tc.task_create_shell(["echo", "hello world"], root=r)
            for _ in range(5)
        ]
    assert task_last(r) == ids[4]
    assert task_recent(root=r) == ids
    assert task_recent(root=r, limit=3) == ids[2:]


def test_can_detect_corrupt_recent_file(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        ids = []
        for i in range(5):
            if i > 0:
                time.sleep(0.01)
            ids.append(tc.task_create_shell(["echo", "hello world"], root=r))
    assert task_recent(root=r) == ids
    with r.path_recent().open("w") as f:
        for i in [*ids[:2], ids[2] + ids[3], ids[4]]:
            f.write(f"{i}\n")
    with pytest.raises(Exception, match="Recent data list is corrupt"):
        task_recent(root=r)
    task_recent_rebuild(root=r)
    assert task_recent(root=r) == ids
    task_recent_rebuild(root=r, limit=3)
    assert task_recent(root=r) == ids[2:]
    task_recent_rebuild(root=r, limit=0)
    assert task_recent(root=r) == []
    task_recent_rebuild(root=r, limit=0)
    assert task_recent(root=r) == []


def test_can_read_driver_for_submitted_task(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["echo", "hello world"], root=r)
    assert task_exists(tid, r)
    assert task_status(tid, r) == TaskStatus.CREATED
    assert task_driver(tid, r) is None
    set_task_status(tid, TaskStatus.SUBMITTED, None, r)
    assert task_driver(tid, r) is None
    set_task_status(tid, TaskStatus.SUBMITTED, "example", r)
    assert task_driver(tid, r) == "example"
    set_task_status(tid, TaskStatus.SUCCESS, None, r)
    assert task_driver(tid, r) == "example"


def test_no_outer_log_without_submission(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["echo", "hello world"], root=r)
    with pytest.raises(Exception, match="outer logs are only available"):
        task_log(tid, outer=True, root=r)


def test_can_validate_task_id():
    assert is_valid_task_id("3852ea7fe8adab595cc5084d29be0bf7")
    assert not is_valid_task_id("3852ea7fe8adab595cc5084d29be0bf")
    assert not is_valid_task_id("3852ea7fe8adab59ri5cc5084d29be0bf7")
    assert not is_valid_task_id(" 3852ea7fe8adab59ri5cc5084d29be0bf7")
    assert check_task_id("3852ea7fe8adab595cc5084d29be0bf7") is None
    with pytest.raises(Exception, match="does not look like a valid task"):
        check_task_id("3852ea7fe8adab595cc5084d29be")
