from string import Template
from typing import TypeAlias

from hipercow.bundle import bundle_create
from hipercow.root import OptionalRoot, open_root
from hipercow.task_create import task_create_shell
from hipercow.util import expand_grid


class _TemplateAt(Template):
    delimiter = "@"

    # Backport a simplified version of get_idenfiers for python 3.10,
    # which lacks this method https://docs.python.org/3/library/string.html
    if not hasattr(Template, "get_identifiers"):  # pragma: no cover

        def get_identifiers(self):
            return _template_identifiers(self)


def _template_identifiers(obj: Template) -> list[str]:
    ids = []
    for mo in obj.pattern.finditer(obj.template):
        named = mo.group("named") or mo.group("braced")
        if named is not None and named not in ids:
            ids.append(named)
    return ids


BulkDataInput: TypeAlias = list[dict[str, str]] | dict[str, str | list[str]]


# ignoring the details of doing the substitutions, this is really all
# we need to do:
def bulk_create_shell(
    cmd_template: list[str],
    data: BulkDataInput,
    *,
    name: str | None = None,
    root: OptionalRoot = None,
    **kwargs,
) -> str:
    """Create a group of tasks from a template and data.

    You may want to use `bulk_crete_shell_commands` to preview the set
    of commands that would be created.

    There are a couple of ways that you might want to load data into
    the template:

    * You might have data in a table (e.g., in a csv file).  In this
      case we might model this as a list of `dict`s, each
      corresponding to a row in the original table.

    * You might have a series of factors that you want to compute all
      possible combinations of.  In this case we might model this as a
      dictionary of lists.

    We will handle either type and try and do the right thing.  This
    necessitates a bit of magic, and we may tone this down in future
    if it ends up being too unpredictable.

    Args:
        cmd_template: A command template.  This should be a list of
            strings, with some containing template placeholders.

        data: A list of dictionaries to substitute into the template.

        name: Optional name for the created bundle.  If `None` (the
            default) then a random name will be created for the bundle.

        root: The root, or if not given search from the current directory.

        kwargs: Additional arguments passed through to
            `hipercow.task_create.task_create_shell`.  This includes
            `environment`, `envvars`, `resources` and `driver`.

    Returns: The name of the created bundle of tasks.  You can use
        `hipercow.bundle.task_bundle_load` to load this and methods in
        `hipercow.bundle` to interact with or query the bundle.

    """
    root = open_root(root)
    cmd = bulk_create_shell_commands(cmd_template, data)
    task_ids = [task_create_shell(cmd_i, **kwargs) for cmd_i in cmd]
    return bundle_create(task_ids, name=name, validate=False, root=root)


def bulk_create_shell_commands(
    cmd_template: list[str], data: BulkDataInput
) -> list[list[str]]:
    """Create a list of commands from a template and data.

    Creates the list of commands (each of which is a list of strings)
    by using a **command template** -- a list of strings containing
    `@{...}` placeholders -- and data to substitute into this.

    You can use this to debug or preview commands that would be
    produced by `bulk_create_shell` without accidentally submitting
    thousands of tasks.

    Args:
        cmd_template: A command template.  This should be a list of
            strings, with some containing template placeholders.

        data: A list of dictionaries or dictionary of lists to
            substitute into the template; see
            `hipercow.task_create_bulk.bulk_create_shell` for details.

    Returns: A list of lists of strings; the `i`th element of this is
        the command substituted from the `i`th element of `data`.

    """
    template = [_TemplateAt(el) for el in cmd_template]

    # Check that all elements in data are consumed by the template

    keys_template = set()
    for el in template:
        keys_template |= set(el.get_identifiers())

    data_list = _check_template_data(data)
    keys_data = set(data_list[0].keys())

    if extra := keys_template - keys_data:
        extra_str = ", ".join(extra)
        msg = f"Template variables not present in data: {extra_str}"
        raise Exception(msg)

    if unused := keys_data - keys_template:
        unused_str = ", ".join(unused)
        msg = f"Data variables not present in template: {unused_str}"
        raise Exception(msg)

    return [[i.substitute(d) for i in template] for d in data_list]


def _check_template_data(data: BulkDataInput) -> list[dict[str, str]]:
    if not data:
        msg = "No data provided"
        raise Exception(msg)

    if isinstance(data, list):
        keys = data[0].keys()
        for el in data[1:]:
            if el.keys() != keys:
                msg = "Inconsistent keys among data"
                raise Exception(msg)
        return data
    else:
        return _bulk_data_combine(data)


def _bulk_data_combine(
    data: dict[str, str | list[str]],
) -> list[dict[str, str]]:
    return expand_grid(
        {k: v if isinstance(v, list) else [v] for k, v in data.items()}
    )
