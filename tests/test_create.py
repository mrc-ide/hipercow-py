import re

import pytest

from hipercow import root
from hipercow import task_create as tc
from hipercow.task import TaskData
from hipercow.util import transient_working_directory


def test_create_simple_task(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(r, ["echo", "hello world"])
    assert re.match("^[0-9a-f]{32}$", tid)
    path_data = tmp_path / "hipercow" / "tasks" / tid[:2] / tid[2:] / "data"
    assert path_data.exists()
    d = TaskData.read(root.open_root(tmp_path), tid)
    assert isinstance(d, TaskData)
    assert d.task_id == tid
    assert d.method == "shell"
    assert d.data == {"cmd": ["echo", "hello world"]}
    assert d.path == "."
    assert d.envvars == {}


def test_tasks_cannot_be_empty(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with pytest.raises(Exception, match="cannot be empty"):
        with transient_working_directory(tmp_path):
            tc.task_create_shell(r, [])
