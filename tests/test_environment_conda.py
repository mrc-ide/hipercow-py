import os
from unittest import mock

import pytest

from hipercow import root
from hipercow.environment import environment_engine, environment_new
from hipercow.environment_engines import Conda, Platform
from hipercow.environment_engines.conda import _micromamba
from hipercow.util import file_create, transient_working_directory


@pytest.fixture
def micromamba(tmp_path, monkeypatch):
    path = tmp_path / "bin" / "micromamba"
    path.parent.mkdir()
    file_create(path)
    monkeypatch.setenv("HIPERCOW_MICROMAMBA", str(path))
    return str(path)


def test_conda_environment_does_not_exist_until_created(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Conda(r, "default")
    assert not env.exists()
    env.path().mkdir(parents=True)
    assert env.exists()


def test_conda_paths_depend_on_platform(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    contents = r.path_environment_contents("default")
    env_linux = Conda(r, "default", Platform("linux", "3.12.0"))
    env_windows = Conda(r, "default", Platform("windows", "3.12.0"))
    assert env_linux.path() == contents / "conda-linux"
    assert env_linux.path_root_prefix() == contents / "mamba-linux"
    assert env_windows.path() == contents / "conda-windows"
    assert env_windows.path_root_prefix() == contents / "mamba-windows"


def test_conda_environment_can_be_created(tmp_path, mocker, micromamba):
    mock_run = mock.MagicMock()
    mocker.patch("subprocess.run", mock_run)

    root.init(tmp_path)
    r = root.open_root(tmp_path)
    environment_new("default", "conda", r)
    env = environment_engine("default", r)
    assert isinstance(env, Conda)

    prefix = str(env.path())
    path_rc = str(env.path_root_prefix() / ".mambarc")
    envvars = {
        "MAMBA_ROOT_PREFIX": str(env.path_root_prefix()),
        "MAMBARC": path_rc,
        "CONDARC": path_rc,
    }
    assert env._envvars() == envvars

    env.create()
    assert mock_run.call_count == 1
    assert mock_run.mock_calls[0] == mock.call(
        [micromamba, "create", "--yes", "--prefix", prefix],
        check=True,
        env=os.environ | envvars,
    )
    path_rc = env.path_root_prefix() / ".mambarc"
    assert path_rc.exists()
    with path_rc.open() as f:
        assert f.read() == "channels:\n  - conda-forge\n"


@pytest.mark.usefixtures("micromamba")
def test_conda_create_preserves_existing_mambarc(tmp_path, mocker):
    mocker.patch("subprocess.run")
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Conda(r, "default")
    path_rc = env.path_root_prefix() / ".mambarc"
    path_rc.parent.mkdir(parents=True)
    with path_rc.open("w") as f:
        f.write("channels:\n  - bioconda\n")
    env.create()
    with path_rc.open() as f:
        assert f.read() == "channels:\n  - bioconda\n"


def test_conda_can_provision_with_conda_command(tmp_path, mocker, micromamba):
    mock_run = mock.MagicMock()
    mocker.patch("subprocess.run", mock_run)
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Conda(r, "default")
    prefix = str(env.path())
    envvars = env._envvars()

    env.provision(["conda", "install", "-c", "bioconda", "samtools"])
    assert mock_run.call_count == 1
    assert mock_run.mock_calls[0] == mock.call(
        [
            micromamba,
            "install",
            "--yes",
            "--prefix",
            prefix,
            "-c",
            "bioconda",
            "samtools",
        ],
        check=True,
        env=os.environ | envvars,
    )

    env.provision(["mamba", "remove", "samtools"])
    assert mock_run.call_count == 2
    assert mock_run.mock_calls[1] == mock.call(
        [micromamba, "remove", "--yes", "--prefix", prefix, "samtools"],
        check=True,
        env=os.environ | envvars,
    )

    env.provision(["conda", "clean", "--all"])
    assert mock_run.call_count == 3
    assert mock_run.mock_calls[2] == mock.call(
        [micromamba, "clean", "--yes", "--all"],
        check=True,
        env=os.environ | envvars,
    )


def test_conda_can_provision_with_pip(tmp_path, mocker, micromamba):
    mock_run = mock.MagicMock()
    mocker.patch("subprocess.run", mock_run)
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Conda(r, "default")
    prefix = str(env.path())

    env.provision(["pip", "install", "tqdm"])
    assert mock_run.call_count == 1
    assert mock_run.mock_calls[0] == mock.call(
        [micromamba, "run", "--prefix", prefix, "pip", "install", "tqdm"],
        env=os.environ | env._envvars(),
        check=True,
    )


def test_conda_run_uses_micromamba_run(tmp_path, mocker, micromamba):
    mock_run = mock.MagicMock()
    mocker.patch("subprocess.run", mock_run)
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Conda(r, "default")
    prefix = str(env.path())

    env.run(["samtools", "--version"], env={"MYVAR": "1"}, cwd=tmp_path)
    assert mock_run.call_count == 1
    assert mock_run.mock_calls[0] == mock.call(
        [micromamba, "run", "--prefix", prefix, "samtools", "--version"],
        cwd=tmp_path,
        check=False,
        env=os.environ | {"MYVAR": "1"} | env._envvars(),
    )


def test_conda_can_determine_sensible_default_cmd(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Conda(r, "default")

    with transient_working_directory(tmp_path):
        with pytest.raises(Exception, match="Can't determine install"):
            env.check_args(None)
        file_create(tmp_path / "environment.yaml")
        assert env.check_args(None) == [
            "conda",
            "install",
            "--file",
            "environment.yaml",
        ]
        file_create(tmp_path / "environment.yml")
        assert env.check_args([]) == [
            "conda",
            "install",
            "--file",
            "environment.yml",
        ]


def test_conda_validates_provisioning_commands(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    env = Conda(r, "default")

    for cmd in [
        ["conda", "install", "samtools"],
        ["mamba", "update", "samtools"],
        ["micromamba", "remove", "samtools"],
        ["conda", "uninstall", "samtools"],
        ["conda", "clean", "--all"],
        ["conda", "install", "-c", "bioconda", "samtools=1.21"],
        ["pip", "install", "tqdm"],
    ]:
        assert env.check_args(cmd) == cmd

    with pytest.raises(Exception, match="Expected first element"):
        env.check_args(["pwd"])
    with pytest.raises(Exception, match="Expected second element"):
        env.check_args(["conda"])
    with pytest.raises(Exception, match="Expected second element"):
        env.check_args(["conda", "create", "samtools"])
    for arg in ["-n", "--name", "-p", "--prefix=/tmp/x", "--root-prefix"]:
        with pytest.raises(Exception, match=f"Don't use '{arg}'"):
            env.check_args(["conda", "install", arg, "x", "samtools"])


def test_can_find_micromamba_from_envvar(micromamba):
    assert _micromamba() == micromamba


def test_error_if_micromamba_envvar_points_to_missing_file(
    tmp_path, monkeypatch
):
    path = str(tmp_path / "micromamba")
    monkeypatch.setenv("HIPERCOW_MICROMAMBA", path)
    with pytest.raises(Exception, match="but this does not exist"):
        _micromamba()


def test_can_find_micromamba_on_path(mocker, monkeypatch):
    monkeypatch.delenv("HIPERCOW_MICROMAMBA", raising=False)
    mock_which = mocker.patch("shutil.which", return_value="/bin/micromamba")
    assert _micromamba() == "/bin/micromamba"
    assert mock_which.mock_calls == [mock.call("micromamba")]


def test_error_if_micromamba_not_found(mocker, monkeypatch):
    monkeypatch.delenv("HIPERCOW_MICROMAMBA", raising=False)
    mocker.patch("shutil.which", return_value=None)
    with pytest.raises(Exception, match="Could not find 'micromamba'"):
        _micromamba()
