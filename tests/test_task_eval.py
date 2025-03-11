import pytest

from hipercow import root
from hipercow import task_create as tc
from hipercow.task import TaskStatus, task_log, task_status
from hipercow.task_eval import task_eval
from hipercow.util import transient_working_directory


def test_can_set_task_status(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["echo", "hello world"], root=r)
    assert task_status(tid, r) == TaskStatus.CREATED
    task_eval(tid, capture=False, root=r)
    assert task_status(tid, r) == TaskStatus.SUCCESS


def test_cant_run_complete_task(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["echo", "hello world"], root=r)
    task_eval(tid, capture=False, root=r)
    msg = f"Can't run '{tid}', which has status 'success'"
    with pytest.raises(Exception, match=msg):
        task_eval(tid, capture=False, root=r)


def test_can_capture_output_to_auto_file(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["echo", "hello world"], root=r)
    task_eval(tid, capture=True, root=r)

    path = r.path_task_log(tid)
    with path.open("r") as f:
        assert f.read().strip() == "hello world"

    assert task_log(tid, root=r) == "hello world\n"


def test_return_information_about_failure_to_find_path(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(["adsfasdfasdfa", "arg"], root=r)
    task_eval(tid, capture=True, root=r)

    path = r.path_task_log(tid)
    assert path.exists()
    assert task_status(tid, r) == TaskStatus.FAILURE
