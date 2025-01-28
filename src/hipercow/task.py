import pickle
from dataclasses import dataclass
from enum import Flag, auto

from hipercow.root import Root
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
    started: float
    finished: float

    def write(self, root: Root, task_id: str):
        with root.path_task_times(task_id).open("wb") as f:
            pickle.dump(self, f)


def task_status(root: Root, task_id: str) -> TaskStatus:
    # check_task_id(task_id)
    path = root.path_task(task_id)
    if not path.exists():
        return TaskStatus.MISSING
    for v, p in STATUS_FILE_MAP.items():
        if (path / p).exists():
            return v
    return TaskStatus.CREATED


def task_log(root: Root, task_id: str) -> str:
    path = root.path_task_log(task_id)
    if not path.exists():
        status = task_status(root, task_id)
        msg = f"Task log for '{task_id}' does not exist (status: {status})"
        raise Exception(msg)
    with path.open() as f:
        return f.read()


def set_task_status(root: Root, task_id: str, status: TaskStatus):
    file_create(root.path_task(task_id) / STATUS_FILE_MAP[status])


@dataclass
class TaskData:
    task_id: str
    method: str  # shell etc
    data: dict
    path: str
    envvars: dict[str, str]

    def write(self, root: Root):
        task_data_write(root, self)

    @staticmethod
    def read(root: Root, task_id: str):
        return task_data_read(root, task_id)


def task_data_write(root: Root, data: TaskData) -> None:
    task_id = data.task_id
    path_task_dir = root.path_task(task_id)
    path_task_dir.mkdir(parents=True, exist_ok=True)
    with root.path_task_data(task_id).open("wb") as f:
        pickle.dump(data, f)


def task_data_read(root: Root, task_id: str) -> TaskData:
    with root.path_task_data(task_id).open("rb") as f:
        return pickle.load(f)
