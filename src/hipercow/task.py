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


STATUS_FILE_MAP = {
    TaskStatus.SUCCESS:  "status-success",
    TaskStatus.FAILURE: "status-failure",
    TaskStatus.CANCELLED: "status-cancelled",
    TaskStatus.RUNNING: "status-running",
    TaskStatus.SUBMITTED: "status-submitted",
}


def task_status(root: Root, task_id: str) -> TaskStatus:
    # check_task_id(task_id)
    path = root.path / "tasks" / task_id
    if not path.exists():
        return TaskStatus.MISSING
    for v, p in STATUS_FILE_MAP.items():
        if (path / p).exists():
            return v
    return TaskStatus.CREATED


def set_task_status(root: Root, task_id: str, status: TaskStatus):
    file_create(root.path / "tasks" / task_id / STATUS_FILE_MAP[status])


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
    path_task_dir = root.path / "tasks" / data.task_id
    path_task_dir.mkdir(parents=True, exist_ok=True)
    with open(path_task_dir / "data", "wb") as f:
        pickle.dump(data, f)


def task_data_read(root: Root, task_id: str) -> TaskData:
    with open(root.path / "tasks" / task_id / "data", "rb") as f:
        return pickle.load(f)
