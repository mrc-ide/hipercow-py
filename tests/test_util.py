from hipercow.util import find_file_descend


def test_find_descend(tmp_path):
    (tmp_path / "a" / "b" / "c" / "d").mkdir(parents=True)
    (tmp_path / "a" / "b" / ".foo").mkdir(parents=True)
    assert (
        find_file_descend(".foo", tmp_path / "a/b/c/d")
        == (tmp_path / "a" / "b").resolve()
    )
    assert find_file_descend(".foo", tmp_path / "a") is None
