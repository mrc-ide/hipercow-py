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
    path_rel = f"hipercow/py/tasks/{tid[:2]}/{tid[2:]}/task_run.bat"
    assert unc == f"//wpia-hn/didehomes/bob/my/project/{path_rel}"
    assert (r.path / path_rel).exists()


def test_can_create_provision_data():
    m = Mount("wpia-hn", "didehomes/bob", "/mnt/nethome")
    path_map = PathMap(Path("some/path"), m, "Q:", "my/project")
    res = batch._template_data_provision("env", "abcde", path_map)
    assert res["environment_name"] == "env"
    assert res["provision_id"] == "abcde"
    assert res["hipercow_root_drive"] == "Q:"
    assert res["hipercow_root_path"] == "/my/project"
    assert (
        res["network_shares_create"] == r"net use Q: \\wpia-hn\didehomes\bob /y"
    )
    assert res["network_shares_delete"] == "net use Q: /delete /y"


def test_can_write_provision_batch(tmp_path):
    m = Mount("wpia-hn", "didehomes/bob", "/mnt/nethome")
    path_map = PathMap(Path("some/path"), m, "Q:", "my/project")

    root.init(tmp_path)
    r = root.open_root(tmp_path)

    unc = batch.write_batch_provision("myenv", "abcdef", path_map, r)
    path_rel = "hipercow/py/env/myenv/provision/abcdef/run.bat"
    assert unc == f"//wpia-hn/didehomes/bob/my/project/{path_rel}"
    assert (r.path / path_rel).exists()
