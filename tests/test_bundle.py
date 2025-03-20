from hipercow import root
from hipercow.bundle import (
    Bundle,
    bundle_create,
    bundle_delete,
    bundle_list,
    bundle_load,
    bundle_status,
    bundle_status_reduce,
)
from hipercow.task_create import task_create_shell
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
