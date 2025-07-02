import platform
import re
import time
from pathlib import Path
from unittest import mock

import click
import pytest
from click.testing import CliRunner

from hipercow import cli, root, task
from hipercow.bundle import bundle_load
from hipercow.driver import list_drivers
from hipercow.resources import TaskResources
from hipercow.task import TaskStatus, set_task_status, task_data_read
from hipercow.task_create import task_create_shell
from hipercow.util import transient_envvars
from tests.helpers import AnyInstanceOf


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
        assert task.task_status(task_id, r) == task.TaskStatus.CREATED


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
        assert task.task_status(task_id, r) == task.TaskStatus.SUCCESS


def test_can_save_and_read_log(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        root.init(".")
        res = runner.invoke(cli.cli_task_create, ["echo", "hello", "world"])
        task_id = res.stdout.strip()

        res = runner.invoke(cli.cli_task_log, task_id)
        assert res.exit_code == 0
        assert res.output == ""

        res = runner.invoke(cli.cli_task_eval, [task_id, "--capture"])
        assert res.exit_code == 0

        res = runner.invoke(cli.cli_task_log, task_id)
        assert res.exit_code == 0
        assert res.output == "hello world\n\n"

        res = runner.invoke(cli.cli_task_log, [task_id, "--outer"])
        assert res.exit_code == 1
        assert "outer logs are only available" in str(res.exception)


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


def test_can_call_cli_dide_authenticate(mocker):
    mocker.patch("hipercow.cli.dide_auth.check")
    mocker.patch("hipercow.cli.dide_auth.clear")
    mocker.patch("hipercow.cli.dide_auth.authenticate")

    runner = CliRunner()

    res = runner.invoke(cli.cli_dide_authenticate, [])
    assert res.exit_code == 0
    assert res.output.strip() == ""
    assert cli.dide_auth.check.call_count == 0
    assert cli.dide_auth.clear.call_count == 0
    assert cli.dide_auth.authenticate.call_count == 1

    res = runner.invoke(cli.cli_dide_authenticate, ["clear"])
    assert res.exit_code == 0
    assert res.output.strip() == ""
    assert cli.dide_auth.check.call_count == 0
    assert cli.dide_auth.clear.call_count == 1
    assert cli.dide_auth.authenticate.call_count == 1

    res = runner.invoke(cli.cli_dide_authenticate, ["check"])
    assert res.exit_code == 0
    assert res.output.strip() == ""
    assert cli.dide_auth.check.call_count == 1
    assert cli.dide_auth.clear.call_count == 1
    assert cli.dide_auth.authenticate.call_count == 1

    res = runner.invoke(cli.cli_dide_authenticate, ["other"])
    assert res.exit_code == 1
    assert "No such action 'other'" in str(res.exception)
    assert cli.dide_auth.check.call_count == 1
    assert cli.dide_auth.clear.call_count == 1
    assert cli.dide_auth.authenticate.call_count == 1


def test_can_run_dide_check(tmp_path, mocker):
    mock_check = mock.Mock()
    mocker.patch("hipercow.cli.dide_check", mock_check)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        res = runner.invoke(cli.cli_dide_check, [])
        assert res.exit_code == 0
        assert mock_check.call_count == 1
        assert mock_check.mock_calls[0] == mock.call()


def test_can_configure_driver(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        res = runner.invoke(cli.init, ".")
        res = runner.invoke(cli.cli_driver_configure, ["example"])
        assert res.exit_code == 0
        assert "Configured hipercow to use 'example'" in res.output

        res = runner.invoke(cli.cli_driver_list, [])
        assert res.exit_code == 0
        assert res.output == "example\n"

        res = runner.invoke(cli.cli_driver_show, [])
        assert res.exit_code == 0
        assert "Configuration for 'example'" in res.output

        res = runner.invoke(cli.cli_driver_unconfigure, ["example"])
        assert res.exit_code == 0
        assert "Removed configuration for 'example'" in res.output

        res = runner.invoke(cli.cli_driver_list, [])
        assert res.exit_code == 0
        assert res.output == "(none)\n"


def test_can_list_environments(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(cli.init, ".")
        runner.invoke(cli.cli_driver_configure, ["example"])
        res = runner.invoke(cli.cli_environment_new, [])
        assert res.exit_code == 0
        assert "Creating environment 'default' using 'pip'" in res.output
        res = runner.invoke(cli.cli_environment_list, [])
        assert res.exit_code == 0
        assert res.output == "default\nempty\n"


def test_can_create_task_in_environment(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        root.init(".")
        r = root.open_root()

        runner.invoke(cli.init, ".")
        res = runner.invoke(cli.cli_environment_new, ["--name", "other"])
        assert res.exit_code == 0

        res = runner.invoke(
            cli.cli_task_create,
            ["echo", "hello", "world", "--environment", "other"],
        )
        assert res.exit_code == 0
        task_id = res.stdout.strip()
        data = task_data_read(task_id, r)
        assert data.environment == "other"


def test_can_provision_environment(tmp_path, mocker):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(cli.init, ".")
        runner.invoke(cli.cli_environment_new, [])

        mock_provision = mock.MagicMock()
        mocker.patch("hipercow.cli.provision", mock_provision)

        res = runner.invoke(cli.cli_environment_provision, [])
        assert res.exit_code == 0
        assert mock_provision.call_count == 1
        assert mock_provision.mock_calls[0] == mock.call(
            "default", [], root=mock.ANY
        )

        res = runner.invoke(
            cli.cli_environment_provision, ["--name=foo", "pip", "install", "."]
        )
        assert res.exit_code == 0
        assert mock_provision.call_count == 2
        assert mock_provision.mock_calls[1] == mock.call(
            "foo", ["pip", "install", "."], root=mock.ANY
        )


def test_can_delete_environment(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(cli.init, ".")
        runner.invoke(cli.cli_driver_configure, ["example"])
        res = runner.invoke(cli.cli_environment_new, ["--name", "other"])
        assert res.exit_code == 0
        assert "Creating environment 'other' using 'pip'" in res.output

        res = runner.invoke(cli.cli_environment_list, [])
        assert res.exit_code == 0
        assert res.output == "empty\nother\n"

        res = runner.invoke(cli.cli_environment_delete, ["--name", "other"])
        assert res.exit_code == 0

        res = runner.invoke(cli.cli_environment_list, [])
        assert res.exit_code == 0
        assert res.output == "empty\n"


def test_can_wait_on_task(tmp_path, mocker):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(cli.init, ".")
        res = runner.invoke(cli.cli_task_create, ["echo", "hello", "world"])
        assert res.exit_code == 0
        task_id = res.stdout.strip()

        mocker.patch("hipercow.cli.task_wait")

        res = runner.invoke(cli.cli_task_wait, [task_id])
        assert res.exit_code == 0
        assert cli.task_wait.call_count == 1
        assert cli.task_wait.mock_calls[0] == mock.call(
            task_id,
            poll=1,
            timeout=None,
            show_log=True,
            progress=True,
        )

        res = runner.invoke(
            cli.cli_task_wait,
            [task_id, "--poll=0.1", "--no-show-log", "--timeout", "200"],
        )
        assert res.exit_code == 0
        assert cli.task_wait.call_count == 2
        assert cli.task_wait.mock_calls[1] == mock.call(
            task_id,
            poll=0.1,
            timeout=200,
            show_log=False,
            progress=True,
        )


def test_can_build_environment(tmp_path, mocker):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(cli.init, ".")

        mock_provision = mock.MagicMock()
        mocker.patch("hipercow.cli.provision_run", mock_provision)

        res = runner.invoke(
            cli.cli_environment_provision_run, ["example", "abcdef"]
        )
        assert res.exit_code == 0
        assert mock_provision.call_count == 1
        assert mock_provision.mock_calls[0] == mock.call(
            "example", "abcdef", mock.ANY
        )


def test_can_create_on_task_and_wait(tmp_path, mocker):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(cli.init, ".")
        mocker.patch("hipercow.cli.task_wait")
        res = runner.invoke(
            cli.cli_task_create, ["--wait", "echo", "hello", "world"]
        )
        assert res.exit_code == 0
        task_id = res.stdout.strip()
        assert cli.task_wait.call_count == 1
        assert cli.task_wait.mock_calls[0] == mock.call(
            task_id,
        )


def test_can_get_last_task(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        root.init(".")
        r = root.open_root()

        # No tasks
        res = runner.invoke(cli.cli_task_last, [])
        assert res.exit_code == 0
        assert res.stdout == ""

        res = runner.invoke(cli.cli_task_recent, [])
        assert res.exit_code == 0
        assert res.stdout == ""

        ids = [task_create_shell(["true"], root=r) for _ in range(5)]

        res = runner.invoke(cli.cli_task_last, [])
        assert res.exit_code == 0
        assert res.stdout == f"{ids[-1]}\n"

        res = runner.invoke(cli.cli_task_recent, [])
        assert res.exit_code == 0
        assert res.stdout == "".join(i + "\n" for i in ids)

        res = runner.invoke(cli.cli_task_recent, ["--limit", 2])
        assert res.exit_code == 0
        assert res.stdout == "".join(i + "\n" for i in ids[-2:])


def test_can_rebuild_recent_list(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        root.init(".")
        r = root.open_root()

        ids = []
        for i in range(5):
            if i > 0:
                time.sleep(0.01)
            ids.append(task_create_shell(["echo", "hello world"], root=r))

        res = runner.invoke(cli.cli_task_recent, [])
        assert res.exit_code == 0
        assert res.stdout == "".join(i + "\n" for i in ids)

        with r.path_recent().open("w") as f:
            for i in [*ids[:2], ids[2] + ids[3], ids[4]]:
                f.write(f"{i}\n")

        res = runner.invoke(cli.cli_task_recent, [])
        assert res.exit_code == 1
        assert res.stdout == ""
        assert (
            str(res.exception) == "Recent data list is corrupt, please rebuild"
        )

        res = runner.invoke(cli.cli_task_recent, ["--rebuild"])
        assert res.exit_code == 0
        assert res.stdout == "".join(i + "\n" for i in ids)


def test_can_call_cli_dide_bootstrap(mocker):
    mocker.patch("hipercow.cli.dide_bootstrap")
    runner = CliRunner()

    res = runner.invoke(cli.cli_dide_bootstrap, [])
    assert res.exit_code == 0
    assert res.output.strip() == ""
    assert cli.dide_bootstrap.call_count == 1
    assert cli.dide_bootstrap.mock_calls[0] == mock.call(
        None, force=False, verbose=True, python_versions=[], platforms=[]
    )

    res = runner.invoke(
        cli.cli_dide_bootstrap, ["myfile", "--verbose", "--force"]
    )
    assert res.exit_code == 0
    assert res.output.strip() == ""
    assert cli.dide_bootstrap.call_count == 2
    assert cli.dide_bootstrap.mock_calls[1] == mock.call(
        "myfile", force=True, verbose=True, python_versions=[], platforms=[]
    )


def test_show_exception(mocker):
    e = Exception("some error")
    mock_sys_exit = mock.MagicMock()
    mocker.patch("sys.exit", mock_sys_exit)
    with transient_envvars({"HIPERCOW_RAW_ERROR": "1"}):
        with pytest.raises(Exception, match="some error"):
            cli._handle_error(e)
    assert mock_sys_exit.call_count == 0


def test_show_small_error_only(capsys, mocker):
    e = Exception("some error")
    mock_sys_exit = mock.MagicMock()
    mock_console = mock.MagicMock()
    mocker.patch("sys.exit", mock_sys_exit)
    mocker.patch("hipercow.cli.console", mock_console)
    with transient_envvars(
        {"HIPERCOW_RAW_ERROR": None, "HIPERCOW_TRACEBACK": None}
    ):
        cli._handle_error(e)
    assert mock_sys_exit.call_count == 1
    assert mock_sys_exit.mock_calls[0] == mock.call(1)
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 2
    assert out[0] == "Error: some error"
    assert out[1] == "For more information, run with 'HIPERCOW_TRACEBACK=1'"


def test_show_nice_traceback(capsys, mocker):
    e = Exception("some error")
    mock_sys_exit = mock.MagicMock()
    mock_console = mock.MagicMock()
    mocker.patch("sys.exit", mock_sys_exit)
    mocker.patch("hipercow.cli.console", mock_console)
    with transient_envvars(
        {"HIPERCOW_RAW_ERROR": None, "HIPERCOW_TRACEBACK": "1"}
    ):
        cli._handle_error(e)
    assert mock_sys_exit.call_count == 1
    assert mock_sys_exit.mock_calls[0] == mock.call(1)
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 1
    assert out[0] == "Error: some error"
    assert len(mock_console.method_calls) == 1
    assert mock_console.method_calls[0] == mock.call.print_exception(
        show_locals=True, suppress=[click]
    )


def test_cli_wrapper_passes_to_exception_handler_on_error(mocker):
    e = Exception("some error")
    mock_handler = mocker.Mock()
    mocker.patch("hipercow.cli.cli", side_effect=e)
    mocker.patch("hipercow.cli._handle_error", mock_handler)
    cli.cli_safe()
    assert mock_handler.call_count == 1
    assert mock_handler.mock_calls[0] == mock.call(e)


def test_can_set_python_version(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        res = runner.invoke(cli.init, ".")

        r = root.open_root()
        v_ok = ".".join(platform.python_version_tuple()[:2])
        v_err = "3.11" if v_ok == "3.10" else "3.10"

        res = runner.invoke(
            cli.cli_driver_configure, ["example", "--python-version", v_err]
        )
        assert res.exit_code == 1
        assert "not the same as the local version" in str(res.exception)
        assert list_drivers(r) == []

        res = runner.invoke(
            cli.cli_driver_configure, ["example", "--python-version", v_ok]
        )
        assert res.exit_code == 0
        assert list_drivers(r) == ["example"]


def test_can_launch_repl(tmp_path, mocker):
    runner = CliRunner()
    mock_repl = mock.MagicMock()
    mocker.patch("hipercow.cli.repl", mock_repl)
    with runner.isolated_filesystem(temp_dir=tmp_path):
        res = runner.invoke(cli.cli_repl, [])
        assert res.exit_code == 0
        assert mock_repl.call_count == 1
        assert mock_repl.mock_calls[0] == mock.call(
            AnyInstanceOf(click.Context),
            prompt_kwargs={"message": "hipercow> ", "history": None},
        )

        runner.invoke(cli.init, ".")
        res = runner.invoke(cli.cli_repl, [])
        assert res.exit_code == 0
        assert mock_repl.call_count == 2
        assert mock_repl.mock_calls[1] == mock.call(
            AnyInstanceOf(click.Context),
            prompt_kwargs={
                "message": "hipercow> ",
                "history": AnyInstanceOf(cli.FileHistory),
            },
        )


def test_can_handle_exception_in_repl(mocker, capsys):
    ctx = mock.Mock()
    args = mock.Mock()
    mock_repl = mock.MagicMock(side_effect=[Exception("some error"), None])
    mocker.patch("hipercow.cli.repl", mock_repl)

    assert cli._repl_call(ctx, args)
    out = capsys.readouterr().out
    assert "Error: some error" in out
    assert mock_repl.call_count == 1
    assert mock_repl.mock_calls[0] == mock.call(ctx, prompt_kwargs=args)

    assert not cli._repl_call(ctx, args)
    out = capsys.readouterr().out
    assert out == ""
    assert mock_repl.call_count == 2
    assert mock_repl.mock_calls[1] == mock.call(ctx, prompt_kwargs=args)


def test_can_control_queue_used_in_task_creation(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        root.init(".")
        r = root.open_root()
        res = runner.invoke(cli.cli_driver_configure, ["example"])

        res = runner.invoke(
            cli.cli_task_create,
            ["echo", "hello", "world", "--queue", "default"],
        )
        assert res.exit_code == 0
        task_id = res.stdout.splitlines()[1]
        data = task_data_read(task_id, r)
        assert data.resources == TaskResources(queue="default")

        res = runner.invoke(
            cli.cli_task_create,
            ["echo", "hello", "world", "--queue", "other"],
        )
        assert res.exit_code == 1
        assert "Queue 'other' is not in valid queue list" in str(res.exception)


def test_can_use_bulk_create(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        root.init(".")
        r = root.open_root()
        res = runner.invoke(
            cli.cli_create_bulk,
            [
                "--name",
                "mybundle",
                "--data",
                "a=1..2",
                "--data",
                "b=x,y",
                "mycmd",
                "@a",
                "c/@{b}/d",
            ],
        )
        assert res.exit_code == 0
        assert re.search("Created bundle '.+' with 4 tasks", res.output)
        bundle = bundle_load("mybundle", root=r)
        assert len(bundle.task_ids) == 4

        res = runner.invoke(cli.cli_bundle_list, [])
        assert res.exit_code == 0
        assert res.output.strip() == "mybundle"

        res = runner.invoke(cli.cli_bundle_delete, ["mybundle"])
        assert res.exit_code == 0

        res = runner.invoke(cli.cli_bundle_list, [])
        assert res.exit_code == 0
        assert res.output.strip() == ""


def test_can_get_bundle_status(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        root.init(".")
        r = root.open_root()
        res = runner.invoke(
            cli.cli_create_bulk,
            [
                "--name",
                "mybundle",
                "--data",
                "a=1..5",
                "echo",
                "@a",
            ],
        )
        assert res.exit_code == 0
        assert re.search("Created bundle '.+' with 5 tasks", res.output)
        bundle = bundle_load("mybundle", root=r)

        set_task_status(bundle.task_ids[3], TaskStatus.SUCCESS, None, r)

        res = runner.invoke(cli.cli_bundle_status, ["mybundle"])
        assert res.exit_code == 0
        status = ["created", "created", "created", "success", "created"]
        assert res.output == "".join(
            f"{id}: {status}\n"
            for id, status in zip(bundle.task_ids, status, strict=False)
        )

        res = runner.invoke(
            cli.cli_bundle_status, ["mybundle", "--summary", "group"]
        )
        assert res.exit_code == 0
        assert res.output == "created: 4\nsuccess: 1\n"

        res = runner.invoke(
            cli.cli_bundle_status, ["mybundle", "--summary", "single"]
        )
        assert res.exit_code == 0
        assert res.output == "created\n"


def test_can_preview_commands():
    runner = CliRunner()
    res = runner.invoke(
        cli.cli_create_bulk,
        [
            "--preview",
            "--data",
            "a=1..3",
            "echo",
            "@a",
        ],
    )
    assert res.exit_code == 0
    lines = res.output.splitlines()
    assert "I would create 3 commands:" in lines[0]
    assert lines[1] == "  1: echo 1"
    assert lines[2] == "  2: echo 2"
    assert lines[3] == "  3: echo 3"


def test_can_summarise_generated_commands():
    runner = CliRunner()
    res = runner.invoke(
        cli.cli_create_bulk,
        [
            "--preview",
            "--data",
            "a=1..10",
            "--data",
            "b=1..5",
            "echo",
            "@a/@{b}",
        ],
    )
    assert res.exit_code == 0
    lines = res.output.splitlines()
    assert "I would create 50 commands:" in lines[0]
    assert lines[1] == "  1: echo 1/1"
    assert lines[2] == "  2: echo 1/2"
    assert lines[3] == "  3: echo 1/3"
    assert lines[4] == "   : ... 44 commands omitted"
    assert lines[5] == "  48: echo 10/3"
    assert lines[6] == "  49: echo 10/4"
    assert lines[7] == "  50: echo 10/5"


def test_can_create_commands_from_csv(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        with open("data.csv", "w") as f:
            f.write("a,b\n1,1\n1,2\n2,2")
        res = runner.invoke(
            cli.cli_create_bulk,
            [
                "--preview",
                "--data=data.csv",
                "echo",
                "@{a}-@{b}",
            ],
        )

        assert res.exit_code == 0
        output = res.output.splitlines()
        assert len(output) == 4
        assert output[1:] == ["  1: echo 1-1", "  2: echo 1-2", "  3: echo 2-2"]


def test_require_at_least_one_data_argument():
    runner = CliRunner()
    res = runner.invoke(
        cli.cli_create_bulk,
        [
            "--preview",
            "echo",
            "hello",
        ],
    )

    assert res.exit_code == 1
    assert str(res.exception) == "Expected at least one '--data' argument"


def test_can_parse_data_argument():
    assert cli._cli_bulk_parse_data_argument("a=1") == ("a", ["1"])
    assert cli._cli_bulk_parse_data_argument("a=1,2") == ("a", ["1", "2"])
    assert cli._cli_bulk_parse_data_argument("a=1:4") == ("a", ["1", "2", "3"])
    assert cli._cli_bulk_parse_data_argument("a=1..4") == (
        "a",
        ["1", "2", "3", "4"],
    )

    with pytest.raises(Exception, match="Failed to parse"):
        cli._cli_bulk_parse_data_argument("a=b=c")

    with pytest.raises(Exception, match="Failed to parse"):
        cli._cli_bulk_parse_data_argument("a")


def test_can_drop_non_breaking_spaces_from_cmd():
    assert cli._clean_cmd(("a", "b")) == ["a", "b"]
    assert cli._clean_cmd(("a", "b\xa0c")) == ["a", "b", "c"]
    assert cli._clean_cmd(("a", "b\xa0c\xa0d")) == ["a", "b", "c", "d"]
