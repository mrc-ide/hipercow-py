"""Functions for interacting with tasks."""

import re
from enum import Flag, auto

import taskwait
from pydantic import BaseModel

from hipercow.driver import load_driver
from hipercow.resources import TaskResources
from hipercow.root import OptionalRoot, Root, open_root
from hipercow.util import file_create, read_file_if_exists


class TaskStatus(Flag):
    """Status of a task.

    Tasks move from `CREATED` to `SUBMITTED` to `RUNNING` to one of
    `SUCCESS` or `FAILURE`.  In addition a task might be `CANCELLED`
    (this could happen from `CREATED`, `SUBMITTED` or `RUNNING`) or
    might be `MISSING` if it does not exist.

    A runnable task is one that we could use `task_eval` with; it
    might be `CREATED` or `SUBMITTED`.

    A terminal task is one that has reached the latest state it will
    reach, and is `SUCCESS`, `FAILURE` or `CANCELLED`.

    """

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
        """Check if a status implies a task can be run."""
        return bool(self & TaskStatus.RUNNABLE)

    def is_terminal(self) -> bool:
        """Check if a status implies a task is completed."""
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


class TaskTimes(BaseModel):
    created: float
    started: float | None
    finished: float | None


def _read_task_times(task_id: str, root: Root):
    path_times = root.path_task_times(task_id)
    if path_times.exists():
        with path_times.open() as f:
            return TaskTimes.model_validate_json(f.read())
    created = root.path_task_data(task_id).stat().st_ctime
    path_task_running = (
        root.path_task(task_id) / STATUS_FILE_MAP[TaskStatus.RUNNING]
    )
    started = (
        path_task_running.stat().st_ctime
        if path_task_running.exists()
        else None
    )
    return TaskTimes(created=created, started=started, finished=None)


def task_exists(task_id: str, root: OptionalRoot = None) -> bool:
    """Test if a task exists.

    A task exists if the `task_id` was used with this hipercow root
    (i.e., if any files associated with it exist).

    Args:
        task_id: The task identifier, a 32-character hex string.
        root: The root, or if not given search from the current directory.

    Returns:
        `True` if the task exists.
    """
    check_task_id(task_id)
    root = open_root(root)
    return root.path_task(task_id).exists()


def task_status(task_id: str, root: OptionalRoot = None) -> TaskStatus:
    """Read task status.

    Args:
        task_id: The task identifier to check, a 32-character hex string.
        root: The root, or if not given search from the current directory.

    Returns:
        The status of the task.
    """
    check_task_id(task_id)
    root = open_root(root)
    path = root.path_task(task_id)
    if not path.exists():
        return TaskStatus.MISSING
    for v, p in STATUS_FILE_MAP.items():
        if (path / p).exists():
            return v
    return TaskStatus.CREATED


def task_log(
    task_id: str, *, outer: bool = False, root: OptionalRoot = None
) -> str | None:
    """Read the task log.

    Not all tasks have logs; tasks that have not yet started (status
    of `CREATED` or `SUBMITTED` and those `CANCELLED` before starting)
    will not have logs, and tasks that were run without capturing
    output will not produce a log either.  Be sure to check if a
    string was returned.

    Args:
        task_id: The task identifier to fetch the log for, a
            32-character hex string.
        outer: Fetch the "outer" logs; these are logs from the
            underlying HPC software before it hands off to hipercow.
        root: The root, or if not given search from the current directory.

    Returns:
        The log as a single string, if present.

    """
    check_task_id(task_id)
    root = open_root(root)
    if not task_exists(task_id, root):
        msg = f"Task '{task_id}' does not exist"
        raise Exception(msg)

    driver = task_driver(task_id, root)
    if not driver:
        if outer:
            msg = "outer logs are only available for tasks with drivers"
            raise Exception(msg)
        return read_file_if_exists(root.path_task_log(task_id))

    dr = load_driver(driver, root)
    return dr.task_log(task_id, outer=outer, root=root)


def set_task_status(
    task_id: str, status: TaskStatus, value: str | None, root: Root
):
    path = root.path_task(task_id) / STATUS_FILE_MAP[status]
    if value is None:
        file_create(path)
    else:
        with path.open("w") as f:
            f.write(value)


class TaskData(BaseModel):
    task_id: str
    method: str  # shell etc
    data: dict
    path: str
    environment: str
    resources: TaskResources | None
    envvars: dict[str, str]


def task_data_write(data: TaskData, root: Root) -> None:
    task_id = data.task_id
    path_task_dir = root.path_task(task_id)
    path_task_dir.mkdir(parents=True, exist_ok=True)
    with root.path_task_data(task_id).open("w") as f:
        f.write(data.model_dump_json())


def task_data_read(task_id: str, root: Root) -> TaskData:
    with root.path_task_data(task_id).open() as f:
        return TaskData.model_validate_json(f.read())


class TaskInfo(BaseModel):
    status: TaskStatus
    data: TaskData
    times: TaskTimes


def task_info(task_id: str, root: OptionalRoot = None) -> TaskInfo:
    check_task_id(task_id)
    root = open_root(root)
    status = task_status(task_id, root)
    if status == TaskStatus.MISSING:
        msg = f"Task '{task_id}' does not exist"
        raise Exception(msg)
    data = task_data_read(task_id, root)
    times = _read_task_times(task_id, root)
    return TaskInfo(status=status, data=data, times=times)


def task_list(
    *, root: OptionalRoot = None, with_status: TaskStatus | None = None
) -> list[str]:
    """List known tasks.

    Warning:
      This function could take a long time to execute on large
      projects with many tasks, particularly on large file systems.
      Because the tasks are just returned as a list of strings, it may
      not be terribly useful either.  Think before building a workflow
      around this.

    Args:
      root: The root to search from.
      with_status: Optional status, or set of statuses, to match

    Returns:
      A list of task identifiers.

    """
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
        value = task_log(self.task_id, root=self.root)
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
    """Wait for a task to complete.

    Args:
        task_id: The task to wait on.
        root: The root, or if not given search from the current directory.
        allow_created: Allow waiting on a task that has status
            `CREATED`.  Normally this is not allowed because a task
            that is `CREATED` (and not `SUBMITTED`) will not start; if
            you pass `allow_created=True` it is expected that you are
            also manually evaluating this task!
        **kwargs (Any): Additional arguments to `taskwait.taskwait`.

    Returns:
        `True` if the task completes successfully, `False` if it
        fails.  A timeout will throw an error.  We return this boolean
        rather than the `TaskStatus` because this generalises to
        multiple tasks.

    """
    check_task_id(task_id)
    root = open_root(root)
    task = TaskWaitWrapper(task_id, root)

    status = task_status(task_id, root)

    if status == TaskStatus.CREATED and not allow_created:
        msg = f"Cannot wait on task '{task_id}' which has not been submitted"
        raise Exception(msg)

    if status.is_terminal():
        return status == TaskStatus.SUCCESS

    result = taskwait.taskwait(task, **kwargs)
    status = TaskStatus[result.status.upper()]

    return status == TaskStatus.SUCCESS


def task_recent_rebuild(
    *, root: OptionalRoot = None, limit: int | None = None
) -> None:
    """Rebuild the list of recent tasks.

    Args:
        root: The root, or if not given search from the current directory.
        limit: The maximum number of tasks to add to the recent
            list. Use `limit=0` to truncate the list.

    Returns:
        Nothing, called for side effects only.

    """
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
    """Return a list of recently created tasks.

    Args:
        root: The root, or if not given search from the current directory.
        limit: The maximum number of tasks to return.

    Return:
        A list of task identifiers.  The most recent tasks will be
        **last** in this list (we might change this in a future
        version - yes, that will be annoying).  Note that this is
        recency in **creation**, not **completion**.

    """
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
    """Return the most recently created task.

    Args:
        root: The root, or if not given search from the current directory.

    Return:
        A task identifier (a 32-character hex string) if any tasks
        have been created (and if the recent task list has not been
        truncated), or `None` if no tasks have been created.

    """
    root = open_root(root)
    task_id = task_recent(limit=1, root=root)
    return task_id[0] if task_id else None


def task_driver(task_id: str, root: Root) -> str | None:
    """Get the driver used to submit a task.

    This may not always be set (e.g., a task was created before a
    driver was configured), in which case we return `None`.

    Args:
        task_id: The task identifier to look up.
        root: The root, or if not given search from the current directory.

    Returns:
        The driver name, if known.  Otherwise `None`.

    """
    path = root.path_task(task_id) / STATUS_FILE_MAP[TaskStatus.SUBMITTED]
    if not path.exists():
        return None
    with path.open() as f:
        value = f.read()
    return value.strip() if value else None


RE_TASK_ID = re.compile("^[0-9a-f]{32}$")


def is_valid_task_id(task_id: str) -> bool:
    return bool(RE_TASK_ID.match(task_id))


def check_task_id(task_id: str) -> None:
    if not is_valid_task_id(task_id):
        msg = f"'{task_id}' does not look like a valid task identifier"
        raise Exception(msg)


def check_task_exists(task_id: str, root: Root):
    if not task_exists(task_id, root):
        msg = f"Task '{task_id}' does not exist"
        raise Exception(msg)
