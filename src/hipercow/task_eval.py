import pickle
import time
from dataclasses import dataclass

from hipercow.environment import environment_engine
from hipercow.root import OptionalRoot, Root, open_root
from hipercow.task import (
    TaskData,
    TaskStatus,
    TaskTimes,
    set_task_status,
    task_data_read,
    task_status,
)


@dataclass
class TaskResult:
    task_id: str
    success: bool
    data: object


def task_eval(
    task_id: str, *, capture: bool, root: OptionalRoot = None
) -> None:
    root = open_root(root)
    data = task_data_read(task_id, root)
    task_eval_data(data, capture=capture, root=root)


def task_eval_data(data: TaskData, *, capture: bool, root: Root) -> None:
    task_id = data.task_id
    status = task_status(task_id, root)
    if not status.is_runnable():
        msg = f"Can't run '{task_id}', which has status '{status}'"
        raise Exception(msg)

    t_created = root.path_task_data(task_id).stat().st_ctime
    t_start = time.time()

    set_task_status(task_id, TaskStatus.RUNNING, None, root)

    assert data.method == "shell"  # noqa: S101
    res = task_eval_shell(data, capture=capture, root=root)

    t_end = time.time()

    status = TaskStatus.SUCCESS if res.success else TaskStatus.FAILURE
    with root.path_task_result(task_id).open("wb") as f:
        pickle.dump(res.data, f)

    times = TaskTimes(created=t_created, started=t_start, finished=t_end)
    with root.path_task_times(task_id).open("w") as f:
        f.write(times.model_dump_json())

    set_task_status(task_id, status, None, root)


def task_eval_shell(data: TaskData, *, capture: bool, root: Root) -> TaskResult:
    cmd = data.data["cmd"]
    env = data.envvars
    path = root.path / data.path
    filename = root.path_task_log(data.task_id) if capture else None
    res = environment_engine(data.environment, root).run(
        cmd, check=False, env=env, cwd=path, filename=filename
    )
    success = res.returncode == 0
    return TaskResult(data.task_id, success, None)
