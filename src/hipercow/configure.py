import pickle

from hipercow.dide.driver import DideWindowsDriver
from hipercow.driver import HipercowDriver, load_driver
from hipercow.example import ExampleDriver
from hipercow.root import OptionalRoot, Root, open_root
from hipercow.util import transient_working_directory


# For now, we'll hard code our two drivers (dide and example).  Later
# we can explore something like using hooks, for example in the style
# of pytest:
# * https://docs.pytest.org/en/stable/how-to/writing_plugins.html#pip-installable-plugins
# * https://packaging.python.org/en/latest/specifications/entry-points/
def configure(name: str, *, root: OptionalRoot = None, **kwargs) -> None:
    root = open_root(root)
    driver = _get_driver(name)
    with transient_working_directory(root.path):
        config = driver(root, **kwargs)
    _write_configuration(config, root)


def unconfigure(name: str, root: OptionalRoot = None) -> None:
    root = open_root(root)
    path = root.path_configuration(name)
    if path.exists():
        path.unlink()
        print(f"Removed configuration for '{name}'")
    else:
        print(
            f"Did not remove configuration for '{name}' as it was not enabled"
        )


def show_configuration(
    driver: str | None = None, root: OptionalRoot = None
) -> None:
    root = open_root(root)
    dr = load_driver(driver, root)
    print(f"Configuration for '{dr.name}'")
    dr.show_configuration()


# ahead of some sort of global store of drivers:
_DRIVERS = {d.name: d for d in [ExampleDriver, DideWindowsDriver]}


def _get_driver(name: str) -> type[HipercowDriver]:
    try:
        return _DRIVERS[name]
    except KeyError:
        msg = f"No such driver '{name}'"
        raise Exception(msg) from None


def _write_configuration(driver: HipercowDriver, root: Root) -> None:
    name = driver.name
    path = root.path_configuration(name)
    exists = path.exists()
    path.parent.mkdir(exist_ok=True, parents=True)
    with path.open("wb") as f:
        pickle.dump(driver, f)
    if exists:
        print(f"Updated configuration for '{name}'")
    else:
        print(f"Configured hipercow to use '{name}'")
