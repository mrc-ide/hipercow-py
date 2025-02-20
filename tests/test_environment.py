from unittest import mock

import pytest

from hipercow import root
from hipercow.configure import configure
from hipercow.environment import (
    Pip,
    Platform,
    environment_create,
    environment_list,
    environment_provision,
)
from hipercow.util import file_create, transient_working_directory


def test_create_pip_environment(tmp_path, capsys):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    assert environment_list(r) == []
    capsys.readouterr()
    environment_create(r, "default", "pip")
    assert capsys.readouterr().out == "Creating environment 'default'\n"
    assert environment_list(r) == ["default"]
    environment_create(r, "default", "pip")
    assert capsys.readouterr().out == "Environment 'default' already exists\n"


def test_require_pip_environment_engine(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with pytest.raises(Exception, match="Only the 'pip' engine is supported"):
        environment_create(r, "default", "conda")


def test_throw_on_provision_if_no_driver(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    environment_create(r, "default", "pip")
    with pytest.raises(Exception, match="No driver configured"):
        environment_provision(r, "default", [])


def test_throw_on_provision_if_no_environment(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    configure(r, "example")
    with pytest.raises(Exception, match="Environment 'default' does not exist"):
        environment_provision(r, "default", [])


def test_provision_with_example_driver(tmp_path, mocker):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    with (r.path / "requirements.txt").open("w") as f:
        f.write("cowsay\n")
    configure(r, "example")
    mock_run = mock.MagicMock()
    mocker.patch("subprocess.run", mock_run)
    environment_create(r, "default", "pip")
    environment_provision(r, "default", [])

    pr = Pip(r, Platform.local(), "default")
    venv_path = str(pr.path())
    env = pr._envvars()

    assert mock_run.call_count == 2
    assert mock_run.mock_calls[0] == mock.call(
        ["python", "-m", "venv", venv_path], check=True
    )
    assert mock_run.mock_calls[1] == mock.call(
        ["pip", "install", "--verbose", "-r", "requirements.txt"],
        env=env,
        check=True,
    )


def test_dont_create_on_second_provision(tmp_path, mocker):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    file_create(r.path / "pyproject.toml")
    configure(r, "example")
    mock_run = mock.MagicMock()
    mocker.patch("subprocess.run", mock_run)

    environment_create(r, "default", "pip")
    pr = Pip(r, Platform.local(), "default")
    pr.path().mkdir(parents=True)

    environment_provision(r, "default", [])
    assert mock_run.call_count == 1

    assert mock_run.mock_calls[0] == mock.call(
        ["pip", "install", "--verbose", "."],
        env=pr._envvars(),
        check=True,
    )


def test_pip_can_detect_reasonable_install(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    pr = Pip(r, Platform.local(), "default")
    with transient_working_directory(tmp_path):
        with pytest.raises(Exception, match="Can't determine install command"):
            pr._check_args(None)
        file_create(r.path / "requirements.txt")
        assert pr._check_args(None) == [
            "pip",
            "install",
            "--verbose",
            "-r",
            "requirements.txt",
        ]
        file_create(r.path / "pyproject.toml")
        assert pr._check_args(None) == ["pip", "install", "--verbose", "."]
        assert pr._check_args([]) == ["pip", "install", "--verbose", "."]
        assert pr._check_args(["pip", "install", "."]) == [
            "pip",
            "install",
            ".",
        ]
        with pytest.raises(Exception, match="Expected first element"):
            assert pr._check_args(["install", "."])
