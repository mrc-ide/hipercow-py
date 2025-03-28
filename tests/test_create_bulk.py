import pytest

from hipercow import root
from hipercow.bundle import bundle_load
from hipercow.task import task_info
from hipercow.task_create_bulk import (
    _bulk_data_combine,
    _template_identifiers,
    _TemplateAt,
    bulk_create_shell,
    bulk_create_shell_commands,
)
from hipercow.util import transient_working_directory


def test_prepare_simple_grid():
    assert _bulk_data_combine({"a": ["0", "1", "2"]}) == [
        {"a": "0"},
        {"a": "1"},
        {"a": "2"},
    ]
    assert _bulk_data_combine({"a": ["0", "1", "2"], "b": "3"}) == [
        {"a": "0", "b": "3"},
        {"a": "1", "b": "3"},
        {"a": "2", "b": "3"},
    ]
    assert _bulk_data_combine({"a": ["0", "1", "2"], "b": ["3", "4"]}) == [
        {"a": "0", "b": "3"},
        {"a": "0", "b": "4"},
        {"a": "1", "b": "3"},
        {"a": "1", "b": "4"},
        {"a": "2", "b": "3"},
        {"a": "2", "b": "4"},
    ]


def test_can_construct_templated_calls():
    cmd = ["cmd", "path/@{a}", "@b"]
    pars = {"a": ["0", "1"], "b": ["2"]}
    data = _bulk_data_combine(pars)
    res = bulk_create_shell_commands(cmd, data)
    assert res == [["cmd", "path/0", "2"], ["cmd", "path/1", "2"]]
    assert bulk_create_shell_commands(cmd, pars) == res


def test_can_raise_if_unexpected_symbols_in_template():
    cmd = ["cmd", "path/@{a}", "@b"]
    pars = {"a": ["0", "1"]}
    pat = "Template variables not present in data: b"
    with pytest.raises(Exception, match=pat):
        bulk_create_shell_commands(cmd, pars)


def test_can_raise_if_unexpected_symbols_in_data():
    cmd = ["cmd", "path/@{a}"]
    pars = {"a": ["0", "1"], "b": ["2", "3"]}
    pat = "Data variables not present in template: b"
    with pytest.raises(Exception, match=pat):
        bulk_create_shell_commands(cmd, pars)


def test_can_raise_if_no_data():
    cmd = ["cmd", "path/@{a}"]
    with pytest.raises(Exception, match="No data provided"):
        bulk_create_shell_commands(cmd, {})
    with pytest.raises(Exception, match="No data provided"):
        bulk_create_shell_commands(cmd, [])


def test_can_raise_if_data_does_not_have_consistent_keys():
    cmd = ["cmd", "path/@{a}", "@b"]
    data = [{"a": "0", "b": "1"}, {"a": "0", "b": "1", "c": "2"}]
    with pytest.raises(Exception, match="Inconsistent keys among data"):
        bulk_create_shell_commands(cmd, data)


def test_can_bulk_create_tasks(tmp_path):
    root.init(tmp_path)
    r = root.open_root(tmp_path)
    data = {"by": ["cow", "horse"], "what": ["hello", "hipercow"]}
    with transient_working_directory(tmp_path):
        nm = bulk_create_shell(
            ["cowsay", "-c", "@by", "-t", "@{what}"],
            data,
        )
    bundle = bundle_load(nm, root=r)
    assert len(bundle.task_ids) == 4
    d0 = task_info(bundle.task_ids[0], root=r)
    assert d0.data.data["cmd"] == ["cowsay", "-c", "cow", "-t", "hello"]
    d1 = task_info(bundle.task_ids[1], root=r)
    assert d1.data.data["cmd"] == ["cowsay", "-c", "cow", "-t", "hipercow"]


def test_can_extract_identrifiers_with_backport():
    obj = _TemplateAt("hello @{a} @b world")
    assert _template_identifiers(obj) == ["a", "b"]
    obj = _TemplateAt("hello @{a} @b world @a")
    assert _template_identifiers(obj) == ["a", "b"]
