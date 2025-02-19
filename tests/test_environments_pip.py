import pytest

from hipercow.environments.pip import PipSource, PipVenv

def test_can_create_default_requirements_source():
    x = PipSource.requirements()
    assert x.args == ["pip", "install", "-r", "requirements.txt"]
    assert x.mode == "requirements"
    assert x.data == {"path": "requirements.txt"}
    assert str(x) == "requirements: path=requirements.txt"


def test_can_create_custom_requiremets_source():
    x = PipSource.requirements("some/path.txt")
    assert x.args == ["pip", "install", "-r", "some/path.txt"]
    assert x.mode == "requirements"
    assert x.data == {"path": "some/path.txt"}
    assert str(x) == "requirements: path=some/path.txt"


def test_can_create_path_source():
    x = PipSource.path()
    assert x.args == ["."]
    assert x.mode == "path"
    assert x.data == {"path": "."}
    assert str(x) == "path: path=."


def test_can_create_custom_path_source():
    x = PipSource.path("foo")
    assert x.args == ["foo"]
    assert x.mode == "path"
    assert x.data == {"path": "foo"}
    assert str(x) == "path: path=foo"


def test_can_describe_pip_venv(capsys):
    e = PipVenv(requirements="requirements.txt")
    e.describe()
    out = capsys.readouterr().out
    assert out == "Pip installation:\nrequirements: path=requirements.txt\n"


def test_can_install_single_source():
    e = PipVenv(requirements="requirements.txt")
    assert e.install() == [["pip", "install", "-r", "requirements.txt"]]


def test_can_create():
    e = PipVenv(requirements="requirements.txt")
    cmd = e.create("foo")
    assert cmd == ["python", "-m", "venv", str(e.path("foo"))]


def test_can_activate():
    e = PipVenv(requirements="requirements.txt")
    assert e.activate("foo", "windows") == ["call", str(e.path("foo") / "Scripts" / "activate.bat")]
    assert e.activate("foo", "linux") == [".", str(e.path("foo") / "bin" / "activate")]
