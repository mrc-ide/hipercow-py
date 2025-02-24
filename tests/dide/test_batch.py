from pathlib import Path

from hipercow import root
from hipercow import task_create as tc
from hipercow.dide import batch
from hipercow.dide.mounts import Mount, PathMap
from hipercow.util import transient_working_directory


def test_can_create_batch_data():
    m = Mount("wpia-hn", "didehomes/bob", "/mnt/nethome")
    path_map = PathMap(Path("some/path"), m, "Q:", "my/project")
    res = batch._template_data_task_run("abcde", path_map)
    assert res["task_id"] == "abcde"
    assert res["task_id_1"] == "ab"
    assert res["task_id_2"] == "cde"
    assert res["hipercow_root_drive"] == "Q:"
    assert res["hipercow_root_path"] == "/my/project"
    assert (
        res["network_shares_create"] == r"net use Q: \\wpia-hn\didehomes\bob /y"
    )
    assert res["network_shares_delete"] == "net use Q: /delete /y"


def test_can_write_batch(tmp_path):
    m = Mount("wpia-hn", "didehomes/bob", "/mnt/nethome")
    path_map = PathMap(Path("some/path"), m, "Q:", "my/project")

    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with transient_working_directory(tmp_path):
        tid = tc.task_create_shell(r, ["echo", "hello world"])

    unc = batch.write_batch_task_run(tid, path_map, r)
    path_rel = f"hipercow/tasks/{tid[:2]}/{tid[2:]}/task_run.bat"
    assert unc == f"//wpia-hn/didehomes/bob/my/project/{path_rel}"
    assert (r.path / path_rel).exists()


def test_can_create_provisioning_batch_data():
    m = Mount("wpia-hn", "didehomes/bob", "/mnt/nethome")
    path_map = PathMap(Path("some/path"), m, "Q:", "my/project")
    res = batch._template_data_provision("example", "abcde", path_map)
    core = batch._template_data_core(path_map)
    assert all(k in res.keys() for k in core.keys())
    extra = {k: v for k, v in res.items() if k not in core}
    assert extra == {"environment_name": "example", "provision_id": "abcde"}


def test_can_write_provisioing_batch(tmp_path):
    m = Mount("wpia-hn", "didehomes/bob", "/mnt/nethome")
    path_map = PathMap(Path("some/path"), m, "Q:", "my/project")

    root.init(tmp_path)
    r = root.open_root(tmp_path)
    id = "abcdef"

    unc = batch.write_batch_provision("example", id, path_map, r)
    path_rel = "hipercow/env/example/provision/abcdef/run.bat"
    assert unc == f"//wpia-hn/didehomes/bob/my/project/{path_rel}"
    assert (r.path / path_rel).exists()
