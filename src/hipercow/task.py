import pickle
from dataclasses import dataclass
from enum import Flag, auto

import taskwait

from hipercow.root import OptionalRoot, Root, open_root
from hipercow.util import file_create


class TaskStatus(Flag):
    CREATED = auto()
    SUBMITTED = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILURE = auto()
    CANCELLED = auto()
    MISSING = auto()
    TERMINAL = SUCCESS | FAILURE | CANCELLED
    RUNNABLE = CREATED | SUBMITTED

    def is_runnable(self) -> bool:
        return bool(self & TaskStatus.RUNNABLE)

    def is_terminal(self) -> bool:
        return bool(self & TaskStatus.TERMINAL)

    def __str__(self) -> str:
        return str(self.name).lower()


STATUS_FILE_MAP = {
    TaskStatus.SUCCESS: "status-success",
    TaskStatus.FAILURE: "status-failure",
    TaskStatus.CANCELLED: "status-cancelled",
    TaskStatus.RUNNING: "status-running",
    TaskStatus.SUBMITTED: "status-submitted",
}


## TODO: we'll probably move these to use json soon via pydantic.
@dataclass
class TaskTimes:
    created: float
    started: float | None
    finished: float | None

    def write(self, task_id: str, root: Root):
        with root.path_task_times(task_id).open("wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def read(task_id: str, root: Root):
        path_times = root.path_task_times(task_id)
        if path_times.exists():
            with path_times.open("rb") as f:
                return pickle.load(f)
        created = root.path_task_data(task_id).stat().st_ctime
        path_task_running = (
            root.path_task(task_id) / STATUS_FILE_MAP[TaskStatus.RUNNING]
        )
        running = (
            path_task_running.stat().st_ctime
            if path_task_running.exists()
            else None
        )
        return TaskTimes(created, running, None)


def task_exists(task_id: str, root: OptionalRoot = None) -> bool:
    root = open_root(root)
    return root.path_task(task_id).exists()


def task_status(task_id: str, root: OptionalRoot = None) -> TaskStatus:
    root = open_root(root)
    # check_task_id(task_id)
    path = root.path_task(task_id)
    if not path.exists():
        return TaskStatus.MISSING
    for v, p in STATUS_FILE_MAP.items():
        if (path / p).exists():
            return v
    return TaskStatus.CREATED


def task_log(task_id: str, root: OptionalRoot) -> str | None:
    root = open_root(root)
    if not task_exists(task_id, root):
        msg = f"Task '{task_id}' does not exist"
        raise Exception(msg)
    path = root.path_task_log(task_id)
    if not path.exists():
        return None
    with path.open() as f:
        return f.read()


def set_task_status(task_id: str, status: TaskStatus, root: Root):
    file_create(root.path_task(task_id) / STATUS_FILE_MAP[status])


@dataclass
class TaskData:
    task_id: str
    method: str  # shell etc
    data: dict
    path: str
    environment: str
    envvars: dict[str, str]

    def write(self, root: Root):
        task_data_write(self, root)

    @staticmethod
    def read(task_id: str, root: Root):
        return task_data_read(task_id, root)


def task_data_write(data: TaskData, root: Root) -> None:
    task_id = data.task_id
    path_task_dir = root.path_task(task_id)
    path_task_dir.mkdir(parents=True, exist_ok=True)
    with root.path_task_data(task_id).open("wb") as f:
        pickle.dump(data, f)


def task_data_read(task_id: str, root: Root) -> TaskData:
    with root.path_task_data(task_id).open("rb") as f:
        return pickle.load(f)


@dataclass
class TaskInfo:
    status: TaskStatus
    data: TaskData
    times: TaskTimes


def task_info(task_id: str, root: OptionalRoot = None) -> TaskInfo:
    root = open_root(root)
    status = task_status(task_id, root)
    if status == TaskStatus.MISSING:
        msg = f"Task '{task_id}' does not exist"
        raise Exception(msg)
    data = TaskData.read(task_id, root)
    times = TaskTimes.read(task_id, root)
    return TaskInfo(status, data, times)


def task_list(
    *, root: OptionalRoot = None, with_status: TaskStatus | None = None
) -> list[str]:
    root = open_root(root)
    contents = root.path_task(None).rglob("data")
    ids = ["".join(el.parts[-3:-1]) for el in contents if el.is_file()]
    if with_status is not None:
        ids = [i for i in ids if task_status(i, root) & with_status]
    return ids


class TaskWaitWrapper(taskwait.Task):
    def __init__(self, task_id: str, root: Root):
        self.root = root
        self.task_id = task_id
        self.status_waiting = {"created", "submitted"}
        self.status_running = {"running"}

    def status(self) -> str:
        return str(task_status(self.task_id, self.root))

    def log(self) -> list[str] | None:
        value = task_log(self.task_id, self.root)
        return value.splitlines() if value else None

    def has_log(self):
        return True


def task_wait(
    task_id: str,
    *,
    root: OptionalRoot = None,
    allow_created: bool = False,
    **kwargs,
) -> bool:
    root = open_root(root)
    task = TaskWaitWrapper(task_id, root)

    status = task_status(task_id, root)

    if status == TaskStatus.CREATED and not allow_created:
        msg = "Cannot wait on task '{task_id}' which has not been submitted"
        raise Exception(msg)

    if status.is_terminal():
        return status == TaskStatus.SUCCESS

    result = taskwait.taskwait(task, **kwargs)
    status = TaskStatus[result.status.upper()]

    return status == TaskStatus.SUCCESS


def task_recent_rebuild(
    *, root: OptionalRoot = None, limit: int | None = None
) -> None:
    root = open_root(root)
    path = root.path_recent()
    if limit is not None and limit == 0:
        if path.exists():
            path.unlink()
        return

    ids = task_list(root=root)
    time = [root.path_task_data(i).stat().st_ctime for i in ids]
    ids = [i for _, i in sorted(zip(time, ids, strict=False))]

    if limit is not None and limit < len(ids):
        ids = ids[-limit:]

    with path.open("w") as f:
        for i in ids:
            f.write(f"{i}\n")


def task_recent(
    *, root: OptionalRoot = None, limit: int | None = None
) -> list[str]:
    root = open_root(root)
    path = root.path_recent()
    if not path.exists():
        return []

    with path.open() as f:
        ids = [i.strip() for i in f.readlines()]

    id_length = 32
    if not all(len(i) == id_length for i in ids):
        msg = "Recent data list is corrupt, please rebuild"
        raise Exception(msg)

    if limit is not None and limit < len(ids):
        ids = ids[-limit:]

    return ids


def task_last(root: OptionalRoot = None) -> str | None:
    root = open_root(root)
    task_id = task_recent(limit=1, root=root)
    return task_id[0] if task_id else None
