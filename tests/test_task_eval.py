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
        tid = tc.task_create_shell(r, ["echo", "hello world"])
    assert task_status(r, tid) == TaskStatus.CREATED
    task_eval(r, tid)
    assert task_status(r, tid) == TaskStatus.SUCCESS


def test_cant_run_complete_task(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(r, ["echo", "hello world"])
    task_eval(r, tid)
    msg = f"Can't run '{tid}', which has status 'success'"
    with pytest.raises(Exception, match=msg):
        task_eval(r, tid)


def test_can_capture_output_to_auto_file(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(r, ["echo", "hello world"])
    task_eval(r, tid, capture=True)

    path = r.path_task_log(tid)
    with path.open("r") as f:
        assert f.read().strip() == "hello world"

    assert task_log(r, tid) == "hello world\n"
