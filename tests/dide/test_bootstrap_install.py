import datetime
import json
import os
import sys
import sysconfig
from pathlib import Path
from unittest import mock

import pytest

from hipercow.dide import bootstrap_install as bi
from hipercow.util import file_create

PYTHON_VERSION = "{}.{}".format(*sys.version_info[:2])
UTC = datetime.timezone.utc


def _args(root: Path, name: str, *extra: str) -> list[str]:
    return [
        "--root",
        str(root),
        "--python-version",
        PYTHON_VERSION,
        "--name",
        name,
        "--uv",
        "/path/to/uv",
        *extra,
        "hipercow",
    ]


def _fake_install(path: Path, *, complete: bool = True) -> None:
    path.mkdir(parents=True)
    if complete:
        file_create(path / bi.METADATA)


def test_refuses_to_run_with_wrong_python(tmp_path, capsys):
    args = _args(tmp_path, "20260101000000-abcd")
    args[3] = "2.7"
    assert bi.main(args) == 1
    assert "Expected python 2.7 but found" in capsys.readouterr().out
    assert not any(tmp_path.iterdir())


def test_refuses_invalid_name(tmp_path, capsys):
    assert bi.main(_args(tmp_path, "../../somewhere")) == 1
    assert "Invalid installation name" in capsys.readouterr().out
    assert not any(tmp_path.iterdir())


def test_refuses_to_overwrite_existing_install(tmp_path, capsys):
    name = "20260101000000-abcd"
    dest = tmp_path / f"python-{PYTHON_VERSION}" / "installs" / name
    _fake_install(dest)
    assert bi.main(_args(tmp_path, name)) == 1
    assert "already exists" in capsys.readouterr().out
    assert (dest / bi.METADATA).exists()


def test_successful_install_becomes_current(tmp_path, mocker, capsys):
    name = "20260101000000-abcd"
    base = tmp_path / f"python-{PYTHON_VERSION}"
    mock_install = mocker.patch(
        "hipercow.dide.bootstrap_install.install", return_value="1.2.3"
    )
    mock_prune = mocker.patch("hipercow.dide.bootstrap_install.prune")

    assert bi.main(_args(tmp_path, name, "--verbose")) == 0

    assert mock_install.mock_calls == [
        mock.call(
            base / "installs" / name, "hipercow", "/path/to/uv", verbose=True
        )
    ]
    assert bi.read_current(base) == name
    assert mock_prune.mock_calls == [
        mock.call(base / "installs", name, mock.ANY)
    ]
    out = capsys.readouterr().out
    assert "There is no current installation" in out
    assert f"hipercow 1.2.3 is now current for python {PYTHON_VERSION}" in out


def test_failed_install_is_removed_and_current_unchanged(
    tmp_path, mocker, capsys
):
    base = tmp_path / f"python-{PYTHON_VERSION}"
    base.mkdir()
    bi.set_current(base, "20250101000000-abcd")
    name = "20260101000000-abcd"
    dest = base / "installs" / name

    def fail(path, target, uv, *, verbose):  # noqa: ARG001
        path.mkdir(parents=True)
        msg = "Command failed with exit code 1"
        raise bi.BootstrapError(msg)

    mocker.patch("hipercow.dide.bootstrap_install.install", side_effect=fail)
    mock_prune = mocker.patch("hipercow.dide.bootstrap_install.prune")

    assert bi.main(_args(tmp_path, name)) == 1

    assert not dest.exists()
    assert bi.read_current(base) == "20250101000000-abcd"
    assert mock_prune.call_count == 0
    out = capsys.readouterr().out
    assert "Current installation is '20250101000000-abcd'" in out
    assert "Installation failed: Command failed with exit code 1" in out


def test_failure_to_prune_does_not_fail_install(tmp_path, mocker, capsys):
    mocker.patch("hipercow.dide.bootstrap_install.install", return_value="1")
    mocker.patch(
        "hipercow.dide.bootstrap_install.prune", side_effect=OSError("oops")
    )
    assert bi.main(_args(tmp_path, "20260101000000-abcd")) == 0
    assert "Failed to remove old installations: oops" in capsys.readouterr().out


def test_install_creates_checks_and_records_environment(tmp_path, mocker):
    dest = tmp_path / "installs" / "20260101000000-abcd"
    python = str(bi.python_path(dest))
    uv = "/path/to/uv"

    def run(cmd, *, capture=False):  # noqa: ARG001
        if cmd[:3] == [uv, "pip", "freeze"]:
            return "click==8.1.0\nhipercow==1.2.3\n"
        if cmd == [uv, "--version"]:
            return "uv 0.9.9\n"
        if cmd[0] == python and cmd[1] == "-c":
            return "1.2.3\n"
        return ""

    mock_copy = mocker.patch(
        "hipercow.dide.bootstrap_install.copy_python",
        side_effect=lambda home, dest: dest.mkdir(parents=True),  # noqa: ARG005
    )
    mock_run = mocker.patch(
        "hipercow.dide.bootstrap_install._run", side_effect=run
    )
    assert bi.install(dest, "hipercow", uv, verbose=False) == "1.2.3"

    assert mock_copy.mock_calls == [mock.call(Path(sys.base_prefix), dest)]
    cmds = [c.args[0] for c in mock_run.mock_calls]
    assert cmds[0] == [uv, "pip", "install", "--python", python, "hipercow"]
    assert cmds[1] == [str(bi.scripts_path(dest, "hipercow")), "--help"]
    assert cmds[3] == [uv, "pip", "freeze", "--python", python]

    with (dest / bi.METADATA).open() as f:
        metadata = json.load(f)
    assert metadata["name"] == "20260101000000-abcd"
    assert metadata["hipercow"] == "1.2.3"
    assert metadata["target"] == "hipercow"
    assert metadata["python_executable"] == python
    assert metadata["uv"] == "uv 0.9.9"
    assert metadata["packages"] == ["click==8.1.0", "hipercow==1.2.3"]


def test_install_passes_verbose_to_uv(tmp_path, mocker):
    dest = tmp_path / "installs" / "20260101000000-abcd"
    dest.mkdir(parents=True)
    mocker.patch("hipercow.dide.bootstrap_install.copy_python")
    mock_run = mocker.patch(
        "hipercow.dide.bootstrap_install._run", return_value=""
    )
    bi.install(dest, "/path/to/hipercow.whl", "uv", verbose=True)
    assert mock_run.mock_calls[0].args[0][-2:] == [
        "--verbose",
        "/path/to/hipercow.whl",
    ]


def test_install_stops_at_first_failure(tmp_path, mocker):
    dest = tmp_path / "installs" / "20260101000000-abcd"
    mocker.patch("hipercow.dide.bootstrap_install.copy_python")
    mock_run = mocker.patch(
        "hipercow.dide.bootstrap_install._run",
        side_effect=["", bi.BootstrapError("failed")],
    )
    with pytest.raises(bi.BootstrapError, match="failed"):
        bi.install(dest, "hipercow", "uv", verbose=False)
    assert mock_run.call_count == 2
    assert not (dest / bi.METADATA).exists()


def test_copy_python_copies_and_unmarks_installation(tmp_path):
    home = tmp_path / "cpython-3.12.0"
    stdlib = Path(
        sysconfig.get_path("stdlib", vars={"installed_base": str(home)})
    )
    stdlib.mkdir(parents=True)
    file_create(stdlib / "os.py")
    file_create(stdlib / "EXTERNALLY-MANAGED")
    if sys.platform != "win32":
        (home / "bin").mkdir()
        file_create(home / "bin" / "python3.12")
        (home / "bin" / "python3").symlink_to("python3.12")

    dest = tmp_path / "installs" / "20260101000000-abcd"
    bi.copy_python(home, dest)

    dest_stdlib = dest / stdlib.relative_to(home)
    assert (dest_stdlib / "os.py").exists()
    assert not (dest_stdlib / "EXTERNALLY-MANAGED").exists()
    assert (stdlib / "EXTERNALLY-MANAGED").exists()
    if sys.platform != "win32":
        link = dest / "bin" / "python3"
        assert link.is_symlink()
        assert os.readlink(link) == "python3.12"


def test_run_reports_output_of_failed_command(capsys):
    cmd = [sys.executable, "-c", "print('hello'); raise SystemExit(3)"]
    with pytest.raises(bi.BootstrapError, match="exit code 3"):
        bi._run(cmd, capture=True)
    assert "hello" in capsys.readouterr().out
    assert bi._run([sys.executable, "-c", "print(1)"], capture=True) == "1\n"


def test_can_set_and_read_current(tmp_path):
    assert bi.read_current(tmp_path) is None
    bi.set_current(tmp_path, "20260101000000-abcd")
    # No trailing newline, so that 'set /p' on windows reads it cleanly
    assert (tmp_path / "current").read_bytes() == b"20260101000000-abcd"
    bi.set_current(tmp_path, "20260201000000-abcd")
    assert bi.read_current(tmp_path) == "20260201000000-abcd"
    assert [p.name for p in tmp_path.iterdir()] == ["current"]


def test_set_current_retries_while_file_in_use(tmp_path, mocker):
    mocker.patch("time.sleep")
    real_replace = os.replace
    errors = [PermissionError("busy"), PermissionError("busy")]

    def replace(src, dst):
        if errors:
            raise errors.pop()
        real_replace(src, dst)

    mock_replace = mocker.patch("os.replace", side_effect=replace)
    bi.set_current(tmp_path, "20260101000000-abcd")
    assert mock_replace.call_count == 3
    assert bi.read_current(tmp_path) == "20260101000000-abcd"


def test_set_current_gives_up_eventually(tmp_path, mocker):
    mocker.patch("time.sleep")
    mocker.patch("os.replace", side_effect=PermissionError("busy"))
    with pytest.raises(PermissionError):
        bi.set_current(tmp_path, "20260101000000-abcd", attempts=3)
    assert not any(tmp_path.iterdir())


def test_prune_keeps_recently_superseded_installs(tmp_path):
    now = datetime.datetime(2026, 3, 1, tzinfo=UTC)
    names = [
        "20260101000000-aaaa",  # superseded 2026-01-15; removed
        "20260115000000-bbbb",  # superseded 2026-02-20; kept
        "20260220000000-cccc",  # current
    ]
    for x in names:
        _fake_install(tmp_path / x)
    bi.prune(tmp_path, names[2], now)
    assert sorted(p.name for p in tmp_path.iterdir()) == names[1:]


def test_prune_never_removes_current(tmp_path):
    now = datetime.datetime(2030, 1, 1, tzinfo=UTC)
    names = ["20260101000000-aaaa", "20260115000000-bbbb"]
    for x in names:
        _fake_install(tmp_path / x)
    # Current is the older one (e.g., someone rolled back), so
    # neither is removed: there is nothing newer than the
    # non-current one.
    bi.prune(tmp_path, names[0], now)
    assert sorted(p.name for p in tmp_path.iterdir()) == names


def test_prune_removes_stale_incomplete_installs(tmp_path):
    now = datetime.datetime(2026, 3, 1, 12, tzinfo=UTC)
    _fake_install(tmp_path / "20260101000000-aaaa", complete=False)
    _fake_install(tmp_path / "20260301000000-bbbb", complete=False)
    _fake_install(tmp_path / "20260301060000-cccc")
    bi.prune(tmp_path, "20260301060000-cccc", now)
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "20260301000000-bbbb",  # might still be installing
        "20260301060000-cccc",
    ]


def test_prune_ignores_unknown_files_and_clears_trash(tmp_path):
    now = datetime.datetime(2030, 1, 1, tzinfo=UTC)
    _fake_install(tmp_path / "20260101000000-aaaa.trash")
    _fake_install(tmp_path / "something-else")
    file_create(tmp_path / "20260101000000-bbbb")
    _fake_install(tmp_path / "20260115000000-cccc")
    bi.prune(tmp_path, "20260115000000-cccc", now)
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "20260101000000-bbbb",
        "20260115000000-cccc",
        "something-else",
    ]


def test_remove_skips_installs_in_use(tmp_path, mocker, capsys):
    path = tmp_path / "20260101000000-aaaa"
    _fake_install(path)
    mocker.patch.object(Path, "rename", side_effect=PermissionError("in use"))
    bi._remove(path)
    assert path.exists()
    assert "may still be in use: in use" in capsys.readouterr().out


def test_created_parses_name():
    assert bi._created("20260102030405-abcd") == datetime.datetime(
        2026, 1, 2, 3, 4, 5, tzinfo=UTC
    )
    with pytest.raises(ValueError, match="Invalid installation name"):
        bi._created("foo")


def test_installation_paths(mocker):
    path = Path("env")
    mocker.patch.object(sys, "platform", "win32")
    assert (
        bi.scripts_path(path, "hipercow") == path / "Scripts" / "hipercow.exe"
    )
    assert bi.python_path(path) == path / "python.exe"
    mocker.patch.object(sys, "platform", "linux")
    assert bi.scripts_path(path, "hipercow") == path / "bin" / "hipercow"
    assert bi.python_path(path) == path / "bin" / "python3"
