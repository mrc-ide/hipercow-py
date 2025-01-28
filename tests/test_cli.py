from pathlib import Path

from click.testing import CliRunner

from hipercow import cli, root, task


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
        res = runner.invoke(cli.create, ["echo", "hello", "world"])
        assert res.exit_code == 0
        task_id = res.stdout.strip()
        assert task.task_status(r, task_id) == task.TaskStatus.CREATED


def test_can_run_task(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        root.init(".")
        r = root.open_root()
        res = runner.invoke(cli.create, ["echo", "hello", "world"])
        assert res.exit_code == 0
        task_id = res.stdout.strip()

        res = runner.invoke(cli.status, task_id)
        assert res.exit_code == 0
        assert res.output.strip() == "created"

        res = runner.invoke(cli.eval, task_id)
        assert res.exit_code == 0
        # It would be good to test that we get the expected output
        # here, and empirically we do.  However we don't seem to get
        # it captured in the runner output, though it is swallowed by
        # something.  I've checked with the capsys fixture and that
        # does not seem to have it either.
        assert task.task_status(r, task_id) == task.TaskStatus.SUCCESS
