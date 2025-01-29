from pathlib import Path

from click.testing import CliRunner

from hipercow import cli, root, task
from hipercow.task import TaskStatus


def test_can_init_repository(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        res = runner.invoke(cli.init, ".")
        assert res.exit_code == 0
        r = root.open_root()
        assert r.path == Path.cwd()
        res.stdout.startswith("Initialised hipercow at .")


def test_can_create_task(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        root.init(".")
        r = root.open_root()
        res = runner.invoke(cli.cli_task_create, ["echo", "hello", "world"])
        assert res.exit_code == 0
        task_id = res.stdout.strip()
        assert task.task_status(r, task_id) == task.TaskStatus.CREATED


def test_can_run_task(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        root.init(".")
        r = root.open_root()
        res = runner.invoke(cli.cli_task_create, ["echo", "hello", "world"])
        assert res.exit_code == 0
        task_id = res.stdout.strip()

        res = runner.invoke(cli.cli_task_status, task_id)
        assert res.exit_code == 0
        assert res.output.strip() == "created"

        res = runner.invoke(cli.cli_task_eval, task_id)
        assert res.exit_code == 0
        # It would be good to test that we get the expected output
        # here, and empirically we do.  However we don't seem to get
        # it captured in the runner output, though it is swallowed by
        # something.  I've checked with the capsys fixture and that
        # does not seem to have it either.
        assert task.task_status(r, task_id) == task.TaskStatus.SUCCESS


def test_can_save_and_read_log(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        root.init(".")
        r = root.open_root()
        res = runner.invoke(cli.cli_task_create, ["echo", "hello", "world"])
        task_id = res.stdout.strip()

        res = runner.invoke(cli.cli_task_eval, [task_id, "--capture"])
        assert res.exit_code == 0

        res = runner.invoke(cli.cli_log, task_id)
        assert res.exit_code == 0
        assert res.output == "hello world\n\n"

        res = runner.invoke(cli.cli_log, [task_id, "--filename"])
        assert res.exit_code == 0
        assert res.output.strip() == str(r.path_task_log(task_id))


def test_can_process_with_status_args():
    assert cli._process_with_status([]) is None
    assert cli._process_with_status(["success"]) == TaskStatus.SUCCESS
    assert (
        cli._process_with_status(["success", "running"])
        == TaskStatus.RUNNING | TaskStatus.SUCCESS
    )


def test_can_list_tasks(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        root.init(".")
        res = runner.invoke(cli.cli_task_create, ["echo", "hello", "world"])
        assert res.exit_code == 0
        task_id = res.stdout.strip()

        res = runner.invoke(cli.cli_task_list, [])
        assert res.exit_code == 0
        assert res.output.strip() == task_id

        res = runner.invoke(cli.cli_task_list, ["--with-status", "created"])
        assert res.exit_code == 0
        assert res.output.strip() == task_id

        res = runner.invoke(cli.cli_task_list, ["--with-status", "running"])
        assert res.exit_code == 0
        assert res.output.strip() == ""
