from hipercow import root
from hipercow import task_create as tc
from hipercow.dide import batch_windows
from hipercow.dide.configuration import dide_configuration
from hipercow.dide.mounts import Mount
from hipercow.util import transient_working_directory


def test_can_create_batch_data(tmp_path):
    path = tmp_path / "my/project"
    root.init(path)
    r = root.open_root(path)
    m = Mount(host="wpia-hn", remote="didehomes/bob", local=tmp_path)
    config = dide_configuration(
        r, mounts=[m], python_version=None, check_credentials=False
    )

    res = batch_windows._template_data_task_run_win("abcde", config)
    assert res["task_id"] == "abcde"
    assert res["task_id_1"] == "ab"
    assert res["task_id_2"] == "cde"
    assert res["hipercow_root_drive"] == "V:"
    assert res["hipercow_root_path"] == "\\my\\project"
    assert (
        res["network_shares_create"] == r"net use V: \\wpia-hn\didehomes\bob /y"
    )
    assert res["network_shares_delete"] == "net use V: /delete /y"


def test_can_write_batch(tmp_path):
    path = tmp_path / "my/project"
    root.init(path)
    r = root.open_root(path)
    m = Mount(host="wpia-hn", remote="didehomes/bob", local=tmp_path)
    config = dide_configuration(
        r, mounts=[m], python_version=None, check_credentials=False
    )

    with transient_working_directory(path):
        tid = tc.task_create_shell(["echo", "hello world"], root=r)

    unc = batch_windows.write_batch_task_run_win(tid, config, r)
    path_rel = f"hipercow\\py\\tasks\\{tid[:2]}\\{tid[2:]}\\task_run.bat"
    assert unc == f"\\\\wpia-hn\\didehomes\\bob\\my\\project\\{path_rel}"
    assert (r.path / path_rel.replace("\\", "/")).exists()


def test_can_create_provision_data(tmp_path):
    path = tmp_path / "my/project"
    root.init(path)
    r = root.open_root(path)
    m = Mount(host="wpia-hn", remote="didehomes/bob", local=tmp_path)
    config = dide_configuration(
        r, mounts=[m], python_version=None, check_credentials=False
    )

    res = batch_windows._template_data_provision_win("env", "abcde", config)
    assert res["environment_name"] == "env"
    assert res["provision_id"] == "abcde"
    assert res["hipercow_root_drive"] == "V:"
    assert res["hipercow_root_path"] == "\\my\\project"
    assert (
        res["network_shares_create"] == r"net use V: \\wpia-hn\didehomes\bob /y"
    )
    assert res["network_shares_delete"] == "net use V: /delete /y"


def test_can_write_provision_batch(tmp_path):
    path = tmp_path / "my/project"
    root.init(path)
    r = root.open_root(path)
    m = Mount(host="wpia-hn", remote="didehomes/bob", local=tmp_path)
    config = dide_configuration(
        r, mounts=[m], python_version=None, check_credentials=False
    )

    unc = batch_windows.write_batch_provision_win("myenv", "abcdef", config, r)
    path_rel = "hipercow\\py\\env\\myenv\\provision\\abcdef\\run.bat"
    assert unc == f"\\\\wpia-hn\\didehomes\\bob\\my\\project\\{path_rel}"
    assert (r.path / path_rel.replace("\\", "/")).exists()
