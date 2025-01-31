import pytest
from pathlib import Path

from hipercow.dide import paths
from hipercow.dide.mounts import Mount

def test_throw_on_remap_if_no_mounts_given():
    mounts = []
    path = Path("/foo/bar")
    with pytest.raises(Exception, match="Can't map local directory"):
        paths._remap_path(path, mounts)
        

def test_can_remap_path():
    mounts = [Mount("host", Path("/hostmount"), Path("/local"))]
    path = Path("/local/path/to/dir")
    res = paths._remap_path(path, mounts)
    assert res == paths.PathMap(Path("/local"), Path("/hostmount"),
                                Path("path/to/dir"))
