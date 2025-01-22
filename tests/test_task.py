from hipercow import root
from hipercow import task_create as tc
from hipercow.task import TaskStatus, set_task_status, task_status
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
