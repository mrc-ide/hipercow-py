from pydantic import BaseModel

from hipercow import ui
from hipercow.driver import _get_driver
from hipercow.root import OptionalRoot, Root, open_root
from hipercow.util import transient_working_directory


# For now, we'll hard code our two drivers (dide and example).  Later
# we can explore something like using hooks, for example in the style
# of pytest:
# * https://docs.pytest.org/en/stable/how-to/writing_plugins.html#pip-installable-plugins
# * https://packaging.python.org/en/latest/specifications/entry-points/
def configure(name: str, *, root: OptionalRoot = None, **kwargs) -> None:
    """Configure a driver.

    Configures a `hipercow` root to use a driver.

    Args:
        name: The name of the driver, `dide-windows` or `dide-linux` are
            the currently provided drivers.
        root: The root, or if not given search from the current directory.
        **kwargs (Any): Arguments passed to, and supported by, your driver.

    Returns:
        Nothing, called for side effects only.
    """
    root = open_root(root)
    driver = _get_driver(name)
    with transient_working_directory(root.path):
        config = driver.configure(root, **kwargs)
    _write_configuration(name, config, root)


def unconfigure(name: str, root: OptionalRoot = None) -> None:
    """Unconfigure (remove) a driver.

    Args:
        name: The name of the driver.  This will be `dide` unless you
            are developing `hipercow` itself :)
        root: The root, or if not given search from the current directory.

    Returns:
        Nothing, called for side effects only.
    """
    root = open_root(root)
    path = root.path_configuration(name)
    if path.exists():
        path.unlink()
        ui.alert_success(f"Removed configuration for '{name}'")
    else:
        ui.alert_warning(
            f"Did not remove configuration for '{name}' as it was not enabled"
        )


def _write_configuration(name: str, config: BaseModel, root: Root) -> None:
    path = root.path_configuration(name)
    exists = path.exists()
    path.parent.mkdir(exist_ok=True, parents=True)
    with path.open("w") as f:
        f.write(config.model_dump_json())
    if exists:
        ui.alert_success(f"Updated configuration for '{name}'")
    else:
        ui.alert_success(f"Configured hipercow to use '{name}'")
