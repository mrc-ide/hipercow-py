from hipercow.task_create_bulk import (
    _bulk_data_combine,
    bulk_create_shell_commands,
)


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
