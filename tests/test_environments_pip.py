import pytest

from hipercow.environments.pip import PipSource, PipVenv

def test_can_create_default_requiremets_source():
    x = PipSource.requirements()
    assert x.args == ["-r", "requirements.txt"]
    assert x.mode == "requirements"
    assert x.data == {"path": "requirements.txt"}
    assert str(x) == "requirements: path=requirements.txt"


def test_can_create_custom_requiremets_source():
    x = PipSource.requirements("some/path.txt")
    assert x.args == ["-r", "some/path.txt"]
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


def test_require_at_least_one_source():
    with pytest.raises(Exception, match="At least one source required"):
        PipVenv([])


def test_can_describe_pip_venv(capsys):
    e = PipVenv(PipSource.requirements())
    e.describe()
    out = capsys.readouterr().out
    assert out == "Pip installation:\nrequirements: path=requirements.txt\n"


def test_can_install_single_source():
    e = PipVenv(PipSource.requirements())
    assert e.install() == [["pip", "install", "-r", "requirements.txt"]]


def test_can_install_multiple_sources():
    e = PipVenv([PipSource.requirements(), PipSource.path()])
    assert e.install() == [["pip", "install", "-r", "requirements.txt"],
                           ["pip", "install", "."]]


def test_can_create():
    e = PipVenv(PipSource.requirements())
    cmd = e.create("foo")
    assert cmd == ["python", "-m", "venv", str(e.path("foo"))]


def test_can_activate():
    e = PipVenv(PipSource.requirements())
    assert e.activate("foo", "windows") == ["call", str(e.path("foo") / "Scripts" / "activate.bat")]
    assert e.activate("foo", "linux") == [".", str(e.path("foo") / "bin" / "activate")]
