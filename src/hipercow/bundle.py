"""Support for bundles of related tasks."""

import secrets
from dataclasses import dataclass

from hipercow import ui
from hipercow.root import OptionalRoot, open_root
from hipercow.task import (
    TaskStatus,
    check_task_exists,
    check_task_id,
    task_status,
)


@dataclass
class Bundle:
    name: str
    task_ids: list[str]


def bundle_create(
    task_ids: list[str],
    name: str | None = None,
    *,
    validate: bool = True,
    overwrite: bool = True,
    root: OptionalRoot = None,
) -> Bundle:
    root = open_root(root)
    if validate:
        for i in task_ids:
            check_task_exists(i, root)
    else:
        for i in task_ids:
            check_task_id(i)
    if name is None:
        # TODO: use something better here
        name = secrets.token_hex(8)

    path = root.path_bundle(name)
    if not overwrite and path.exists():
        msg = f"Bundle '{name}' exists and overwrite is False"
        raise Exception(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        f.writelines("".join([f"{el}\n" for el in task_ids]))
    ui.alert_success(f"Created bundle '{name}' with {len(task_ids)} tasks")
    return Bundle(name, task_ids)


def bundle_load(name: str, root: OptionalRoot = None) -> Bundle:
    root = open_root(root)
    path = root.path_bundle(name)
    if not path.exists():
        msg = f"No such bundle '{name}'"
        raise Exception(msg)
    with path.open() as f:
        task_ids = [el.strip() for el in f.readlines()]
    return Bundle(name, task_ids)


def bundle_list(root: OptionalRoot = None) -> list[str]:
    root = open_root(root)
    path = root.path_bundle(None)
    # We could/should order by time here; we do a similar thing with
    # recent tasks.  Alternatively we might want a verbose mode that
    # stores this?  Or we could store time within the bundle, that
    # might make more sense but requiring serialising out as json,
    # possibly with pydantic?  Certainly this metadata would make
    # bundles more useful.
    nms = [x.name for x in path.glob("*")]
    return nms


def bundle_delete(name: str, root: OptionalRoot = None) -> None:
    root = open_root(root)
    path = root.path_bundle(name)
    if path.exists():
        path.unlink()
        ui.alert_success("Deleted bundle '{name}'")
    else:
        ui.alert_danger("No such bundle '{name}'")


def bundle_status(name: str, root: OptionalRoot = None) -> list[TaskStatus]:
    bundle = bundle_load(name, root)
    return [task_status(i) for i in bundle.task_ids]


def bundle_status_reduce(name: str, root: OptionalRoot = None) -> TaskStatus:
    status = bundle_status(name, root)
    return _status_reduce(status)


def _status_reduce(status: list[TaskStatus]) -> TaskStatus:
    order = [
        TaskStatus.CREATED,
        TaskStatus.FAILURE,
        TaskStatus.CANCELLED,
        TaskStatus.RUNNING,
        TaskStatus.SUBMITTED,
        TaskStatus.SUCCESS,
    ]
    return order[min(order.index(i) for i in status)]


# Not implemented - result, cancel, wait, logs, retry
