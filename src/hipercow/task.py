import pickle
from dataclasses import dataclass

from hipercow.root import Root


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
    path_task_dir = root.path / "tasks"
    path_task_dir.mkdir(parents=True, exist_ok=True)
    with open(path_task_dir / data.task_id, "wb") as f:
        pickle.dump(data, f)


def task_data_read(root: Root, task_id: str) -> TaskData:
    with open(root.path / "tasks" / task_id, "rb") as f:
        return pickle.load(f)
