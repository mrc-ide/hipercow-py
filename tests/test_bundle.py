import pytest

from hipercow import root
from hipercow.bundle import (
    bundle_create,
    bundle_delete,
    bundle_list,
    bundle_load,
    bundle_status,
    bundle_status_reduce,
)
from hipercow.task import TaskStatus
from hipercow.task_create import _new_task_id, task_create_shell
from hipercow.util import transient_working_directory


def test_can_create_simple_bundle(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        ids = [task_create_shell(["true"], root=r) for _ in range(5)]
    nm = bundle_create(ids, root=r)
    bundle = bundle_load(nm, root=r)
    assert bundle.name == nm
    assert bundle.task_ids == ids
    assert bundle_list(r) == [nm]


def test_throw_if_load_missing_bundle(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with pytest.raises(Exception, match="No such bundle 'foo'"):
        bundle_load("foo", root=r)


def test_can_delete_bundle(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        ids = [task_create_shell(["true"], root=r) for _ in range(5)]
    nm = bundle_create(ids, root=r)
    assert bundle_list(r) == [nm]
    bundle_delete(nm, root=r)
    assert bundle_list(r) == []


def test_throw_if_delete_missing_bundle(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with pytest.raises(Exception, match="Can't delete bundle 'foo', it"):
        bundle_delete("foo", root=r)


def test_get_bundle_status(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        ids = [task_create_shell(["true"], root=r) for _ in range(5)]
    nm = bundle_create(ids, root=r)
    assert bundle_status(nm, root=r) == [TaskStatus.CREATED] * 5
    assert bundle_status_reduce(nm, root=r) == TaskStatus.CREATED


def test_can_overwrite_bundle(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        ids = [task_create_shell(["true"], root=r) for _ in range(5)]
    nm = bundle_create(ids[:2], root=r)
    assert bundle_load(nm, root=r).task_ids == ids[:2]
    bundle_create(ids[:3], name=nm, overwrite=True, root=r)
    assert bundle_load(nm, root=r).task_ids == ids[:3]
    with pytest.raises(Exception, match="exists and overwrite is False"):
        bundle_create(ids[:4], name=nm, overwrite=False, root=r)
    assert bundle_load(nm, root=r).task_ids == ids[:3]


def test_can_skip_validation(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)

    ids = [_new_task_id() for _ in range(5)]
    with pytest.raises(Exception, match="does not exist"):
        bundle_create(ids, root=r)
    nm = bundle_create(ids, validate=False, root=r)
    assert bundle_load(nm, root=r).task_ids == ids
