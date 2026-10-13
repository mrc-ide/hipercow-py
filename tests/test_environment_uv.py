import os
import subprocess
from pathlib import Path
from unittest import mock

import pytest
from uv import find_uv_bin

from hipercow import root
from hipercow.environment import environment_engine, environment_new
from hipercow.environment_engines import Pip, Platform, Uv
from hipercow.environment_engines.uv import _uv
from hipercow.util import file_create, transient_working_directory


def test_uv_environment_does_not_exist_until_created(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Uv(r, "default")
    assert not env.exists()
    env.path().mkdir(parents=True)
    assert env.exists()


def test_uv_paths_depend_on_platform(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    contents = r.path_environment_contents("default")
    env_linux = Uv(r, "default", Platform("linux", "3.12.0"))
    env_windows = Uv(r, "default", Platform("windows", "3.12.0"))
    assert env_linux.path() == contents / "venv-linux"
    assert env_linux.path_uv() == contents / "uv-linux"
    assert env_windows.path() == contents / "venv-windows"
    assert env_windows.path_uv() == contents / "uv-windows"
    assert env_linux.path_python() == (contents / "uv-linux" / "python" / "bin" / "python3")
    assert env_windows.path_python() == (contents / "uv-windows" / "python" / "python.exe")


def test_uv_envvars_keep_everything_in_environment(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Uv(r, "default", python="3.12")
    path_uv = env.path_uv()
    # Once created, every command uses the environment's own python
    assert env._uv_envvars() == {
        "UV_CACHE_DIR": str(path_uv / "cache"),
        "UV_PYTHON": str(env.path_python().absolute()),
        "UV_PYTHON_DOWNLOADS": "never",
        "UV_PROJECT_ENVIRONMENT": str(env.path()),
    }
    # While creating, uv chooses python and downloads it to 'path'
    assert env._uv_envvars_download(tmp_path / "x") == {
        "UV_CACHE_DIR": str(path_uv / "cache"),
        "UV_PYTHON_INSTALL_DIR": str(tmp_path / "x"),
        "UV_MANAGED_PYTHON": "1",
        "UV_PYTHON": "3.12",
    }
    env = Uv(r, "default")
    assert "UV_PYTHON" not in env._uv_envvars_download(tmp_path / "x")


def test_uv_environment_can_be_created(tmp_path, mocker):
    # A stand-in for the python that uv downloads
    home = tmp_path / "downloaded" / "cpython-3.12.0"
    (home / "bin").mkdir(parents=True)
    file_create(home / "bin" / "python3")

    def run(cmd, **kwargs):  # noqa: ARG001
        if cmd[1:3] == ["-c", "import sys; print(sys.base_prefix)"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=f"{home}\n")
        return mock.DEFAULT

    mock_run = mock.MagicMock(side_effect=run)
    mocker.patch("subprocess.run", mock_run)

    root.init(tmp_path / "root")
    file_create(tmp_path / "root" / "requirements.txt")
    r = root.open_root(tmp_path / "root")
    environment_new("default", "uv", r, python="3.12")
    env = environment_engine("default", r)
    assert isinstance(env, Uv)
    assert env.python == "3.12"

    uv = find_uv_bin()
    venv_path = str(env.path())
    envvars = os.environ | env._uv_envvars()

    env.create()
    assert mock_run.call_count == 3
    # 1. uv chooses and downloads python, into a temporary directory
    cmd, kwargs = mock_run.mock_calls[0].args[0], mock_run.mock_calls[0].kwargs
    assert cmd[:2] == [uv, "venv"]
    tmp = Path(cmd[2]).parent
    assert kwargs["env"]["UV_PYTHON_INSTALL_DIR"] == str(tmp / "python")
    assert kwargs["env"]["UV_PYTHON"] == "3.12"
    # 2. we find out where it is
    exe = "python.exe" if env.platform.system == "windows" else "python"
    assert mock_run.mock_calls[1].args[0][0] == str(tmp / "venv" / env._venv_bin_dir() / exe)
    # 3. the environment is created from the copy
    assert mock_run.mock_calls[2] == mock.call(
        [uv, "venv", "--python", str(env.path_python().absolute()), venv_path],
        check=True,
        env=envvars,
    )
    assert (env.path_uv() / "python" / "bin" / "python3").exists()
    assert not tmp.exists()

    with transient_working_directory(tmp_path / "root"):
        cmd = env.check_args(None)
        assert cmd == ["pip", "install", "-r", "requirements.txt"]
        env.provision(cmd)
        assert mock_run.call_count == 4
        assert mock_run.mock_calls[3] == mock.call(
            [
                uv,
                "pip",
                "install",
                "--python",
                venv_path,
                "-r",
                "requirements.txt",
            ],
            check=True,
            env=envvars,
        )


def test_uv_provision_translates_commands(tmp_path, mocker):
    mock_run = mock.MagicMock()
    mocker.patch("subprocess.run", mock_run)

    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Uv(r, "default")
    uv = find_uv_bin()
    venv_path = str(env.path())
    envvars = os.environ | env._uv_envvars()

    env.provision(["uv", "pip", "uninstall", "-y", "cowsay"])
    assert mock_run.mock_calls[0] == mock.call(
        [uv, "pip", "uninstall", "--python", venv_path, "-y", "cowsay"],
        check=True,
        env=envvars,
    )

    # 'uv sync' finds the environment through UV_PROJECT_ENVIRONMENT
    env.provision(["uv", "sync", "--locked"])
    assert mock_run.mock_calls[1] == mock.call([uv, "sync", "--locked"], check=True, env=envvars)

    env.provision(["uv", "cache", "clean"])
    assert mock_run.mock_calls[2] == mock.call([uv, "cache", "clean"], check=True, env=envvars)


def test_uv_runs_tasks_like_pip(tmp_path, mocker):
    mock_run = mock.MagicMock()
    mocker.patch("subprocess.run", mock_run)

    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Uv(r, "default", python="3.12")
    env.run(["cowsay", "-t", "hello"])
    assert mock_run.mock_calls[0] == mock.call(
        ["cowsay", "-t", "hello"],
        check=False,
        env=os.environ | Pip(r, "default")._envvars(),
    )


def test_uv_can_determine_sensible_default_cmd(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Uv(r, "default")

    with transient_working_directory(tmp_path):
        with pytest.raises(Exception, match="Can't determine install"):
            env.check_args(None)
        file_create(tmp_path / "requirements.txt")
        assert env.check_args(None) == [
            "pip",
            "install",
            "-r",
            "requirements.txt",
        ]
        file_create(tmp_path / "pyproject.toml")
        assert env.check_args([]) == ["pip", "install", "."]
        file_create(tmp_path / "uv.lock")
        assert env.check_args(None) == ["uv", "sync", "--locked"]


def test_uv_check_args_accepts_pip_and_uv_commands(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Uv(r, "default")

    for cmd in [
        ["pip", "install", "cowsay"],
        ["pip", "uninstall", "-y", "cowsay"],
        ["pip", "list"],
        ["uv", "pip", "install", "--index-url", "https://example.com", "x"],
        ["uv", "sync"],
        ["uv", "sync", "--locked", "--no-dev"],
        ["uv", "cache", "clean"],
    ]:
        assert env.check_args(cmd) == cmd


def test_uv_check_args_rejects_invalid_commands(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Uv(r, "default")

    with pytest.raises(Exception, match="to be 'pip' or 'uv'"):
        env.check_args(["conda", "install", "x"])
    with pytest.raises(Exception, match="'cache', 'pip', 'sync'"):
        env.check_args(["uv"])
    with pytest.raises(Exception, match="'cache', 'pip', 'sync'"):
        env.check_args(["uv", "run", "python"])
    with pytest.raises(Exception, match="'pip' to be followed by"):
        env.check_args(["pip"])
    with pytest.raises(Exception, match="'pip' to be followed by"):
        env.check_args(["pip", "download", "x"])
    with pytest.raises(Exception, match="'pip' to be followed by"):
        env.check_args(["uv", "pip"])


def test_uv_check_args_rejects_location_args(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Uv(r, "default")

    for cmd in [
        ["pip", "install", "--python", "3.12", "x"],
        ["pip", "install", "--python=3.12", "x"],
        ["pip", "install", "-p", "3.12", "x"],
        ["pip", "install", "--system", "x"],
        ["pip", "install", "--target", "lib", "x"],
        ["pip", "install", "--prefix", "lib", "x"],
        ["uv", "sync", "--python", "3.12"],
    ]:
        with pytest.raises(Exception, match="hipercow manages the location"):
            env.check_args(cmd)


def test_uv_executable_can_be_overridden(tmp_path, monkeypatch):
    monkeypatch.delenv("HIPERCOW_UV", raising=False)
    assert _uv() == find_uv_bin()
    path = tmp_path / "uv"
    monkeypatch.setenv("HIPERCOW_UV", str(path))
    with pytest.raises(Exception, match="'HIPERCOW_UV' is set to"):
        _uv()
    file_create(path)
    assert _uv() == str(path)
