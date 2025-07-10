from hipercow import root
from hipercow import task_create as tc
from hipercow.dide import batch_linux
from hipercow.dide.configuration import dide_configuration
from hipercow.dide.mounts import Mount
from hipercow.util import transient_working_directory


def test_can_create_batch_data(tmp_path):
    path = tmp_path / "my/project"
    root.init(path)
    r = root.open_root(path)
    m = Mount(host="wpia-san04", remote="homes/bob", local=tmp_path)
    config = dide_configuration(
        r, mounts=[m], python_version=None, check_credentials=False
    )

    res = batch_linux._template_data_task_run_linux("abcde", config)
    assert res["task_id"] == "abcde"
    assert res["task_id_1"] == "ab"
    assert res["task_id_2"] == "cde"
    assert res["hipercow_root_path"] == "/didehomes/bob/my/project/"


def test_can_write_batch(tmp_path):
    path = tmp_path / "my/project"
    root.init(path)
    r = root.open_root(path)
    m = Mount(host="wpia-hn", remote="project/bob", local=tmp_path)
    config = dide_configuration(
        r, mounts=[m], python_version=None, check_credentials=False
    )

    with transient_working_directory(path):
        tid = tc.task_create_shell(["echo", "hello world"], root=r)

    run_sh = batch_linux.write_batch_task_run_linux(tid, config, r)
    path_rel = f"hipercow/py/tasks/{tid[:2]}/{tid[2:]}/task_run.sh"
    assert run_sh == f"/wpia-hn/project/bob/my/project/{path_rel}"
    assert (r.path / path_rel).exists()


def test_can_create_provision_data(tmp_path):
    path = tmp_path / "my/project"
    root.init(path)
    r = root.open_root(path)
    m = Mount(host="wpia-hn2", remote="project/bob", local=tmp_path)
    config = dide_configuration(
        r, mounts=[m], python_version=None, check_credentials=False
    )

    res = batch_linux._template_data_provision_linux("env", "abcde", config)
    assert res["environment_name"] == "env"
    assert res["provision_id"] == "abcde"
    assert res["hipercow_root_path"] == "/wpia-hn2/project/bob/my/project/"


def test_can_write_provision_batch(tmp_path):
    path = tmp_path / "my/project"
    root.init(path)
    r = root.open_root(path)
    m = Mount(host="qdrive", remote="homes/bob", local=tmp_path)
    config = dide_configuration(
        r, mounts=[m], python_version=None, check_credentials=False
    )

    run_sh = batch_linux.write_batch_provision_linux(
        "myenv", "abcdef", config, r
    )
    path_rel = "hipercow/py/env/myenv/provision/abcdef/run.sh"
    assert run_sh == f"/didehomes/bob/my/project/{path_rel}"
    assert (r.path / path_rel).exists()
