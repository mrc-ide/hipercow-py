import sys
from functools import reduce
from operator import ior

import click
from click_repl import repl  # type: ignore
from prompt_toolkit.history import FileHistory
from rich.console import Console
from typing_extensions import Never  # 3.10 does not have this in typing

from hipercow import root
from hipercow.configure import configure, show_configuration, unconfigure
from hipercow.dide import auth as dide_auth
from hipercow.dide.bootstrap import bootstrap as dide_bootstrap
from hipercow.driver import list_drivers
from hipercow.environment import (
    environment_delete,
    environment_list,
    environment_new,
)
from hipercow.provision import provision, provision_run
from hipercow.resources import TaskResources
from hipercow.task import (
    TaskStatus,
    task_last,
    task_list,
    task_log,
    task_recent,
    task_recent_rebuild,
    task_status,
    task_wait,
)
from hipercow.task_create import task_create_shell
from hipercow.task_eval import task_eval
from hipercow.util import loop_while, truthy_envvar

# This is how the 'rich' docs drive things:
console = Console()


# I (Rich) am surprised that there's no really nice way of doing
# something like this out of the box in click.  The idea that we try
# to implement here:
#
# In most cases where an error is thrown we print the immediate
# exception and set the exit code to 1.
#
# Additionally: if the user sets an environment variable, then we show
# the trace; we can use this for getting additional debug information
# out.
#
# Finally, I've added an option here to just not do anything
# interesting with the output and follow click's normal exception
# handling.
def cli_safe():
    try:
        cli()
    except Exception as e:
        _handle_error(e)


def _handle_error(e: Exception) -> Never:
    if truthy_envvar("HIPERCOW_RAW_ERROR"):
        raise e
    else:
        click.echo(f"Error: {e}")
        if truthy_envvar("HIPERCOW_TRACEBACK"):
            console.print_exception(show_locals=True, suppress=[click])
        else:
            click.echo("For more information, run with 'HIPERCOW_TRACEBACK=1'")
        sys.exit(1)


@click.group()
@click.version_option()
def cli():
    """Interact with hipercow."""
    pass  # pragma: no cover


@cli.command()
@click.argument("path", default=".")
def init(path: str):
    """Initialise a new `hipercow` root.

    Create a new `hipercow` root at the path `path`.  This path should
    be the root directory of your project (e.g., the path containing
    `.git`) and we will create a directory `hipercow/` within that
    directory.

    Once initialised, you should configure a driver and environment.

    The default is to initialise at the current directory, like `git`
    would.

    """
    root.init(path)


@cli.command("repl")
@click.pass_context
def cli_repl(ctx):
    """Launch the interactive REPL.

    Running this creates an interactive session where you can send a
    series of commands to `hipercow`, with nice autocompletion.
    Please let us know how you find this.

    Type `:help` for help within the REPL.  To quit, type `:exit` or
    Ctrl-D.

    """
    prompt_kwargs = {"message": "hipercow> ", "history": _repl_history()}
    loop_while(lambda: _repl_call(ctx, prompt_kwargs))


def _repl_history():
    try:
        r = root.open_root()
        return FileHistory(r.path_repl_history())
    except Exception:
        return None


def _repl_call(ctx, prompt_kwargs) -> bool:
    try:
        repl(ctx, prompt_kwargs=prompt_kwargs)
        return False
    except Exception as e:
        click.echo(f"Error: {e}")
        return True


@cli.group()
def driver():
    """Configure drivers."""
    pass  # pragma: no cover


@driver.command("configure")
@click.argument("name")
@click.option("--python-version", help="Python version to use on the cluster")
def cli_driver_configure(name: str, python_version: str | None):
    """Add a driver.

    This command will initialise a driver.  Most likely you will call

        hipercow driver configure dide-windows

    because `dide-windows` is the only real driver at the moment.  If
    you provide the `--python-version` flag you can specify the Python
    version to use, if you want a version that is different to the
    version of Python that you are using locally.

    """
    configure(name, python_version=python_version)


@driver.command("unconfigure")
@click.argument("name")
def cli_driver_unconfigure(name: str):
    """Unconfigure (remove) a driver."""
    unconfigure(name)


@driver.command("show")
@click.argument("name", required=False)
def cli_driver_show(name: str | None):
    """Show configuration for a driver."""
    show_configuration(name)


@driver.command("list")
def cli_driver_list():
    """List configured drivers."""
    drivers = list_drivers(root.open_root())
    if drivers:
        click.echo("\n".join([str(d) for d in drivers]))
    else:
        click.echo("(none)")


@cli.group()
def task():
    """Create and interact with tasks."""
    pass  # pragma: no cover


@task.command("status")
@click.argument("task_id")
def cli_task_status(task_id: str):
    """Get the status of a task.

    The `task_id` will be a 32-character hex string.  We print a
    single status as a result, this might be `created`, `submitted`,
    `running`, `success` or `failure`.  Additional statuses will be
    added in future as we expand the tool.

    """
    click.echo(task_status(task_id))


@task.command("log")
@click.option(
    "--outer", is_flag=True, help="Print the outer logs, from the HPC system"
)
@click.argument("task_id")
def cli_task_log(task_id: str, *, outer=False):
    """Get a task log.

    If the log does not yet exist, we return nothing.

    """
    value = task_log(task_id, outer=outer)
    if value is not None:
        click.echo(value)


@task.command("list")
@click.option("--with-status", type=str, multiple=True)
def cli_task_list(with_status=None):
    """List all tasks.

    This is mostly meant for debugging; the task list is not very
    interesting and it might take a while to find them all.

    """
    with_status = _process_with_status(with_status)
    for task_id in task_list(with_status=with_status):
        click.echo(task_id)


@task.command("last")
def cli_task_last():
    """List the most recently created task."""
    task_id = task_last()
    if task_id is None:
        # we might set exit code to something nonzero here, but this
        # seems slightly hard...
        pass
    else:
        click.echo(task_id)


@task.command("recent")
@click.option(
    "--limit", type=int, default=10, help="The maximum number of tasks to list"
)
@click.option("--rebuild", is_flag=True, help="Rebuild the recent task list")
def cli_task_recent(limit: int, *, rebuild: bool):
    """List recent tasks."""
    if rebuild:
        task_recent_rebuild(limit=limit)
    for i in task_recent(limit=limit):
        click.echo(i)


@task.command("create")
@click.argument("cmd", nargs=-1)
@click.option(
    "--environment", type=str, help="The environment in which to run the task"
)
@click.option("--queue", help="Queue to submit the task to")
@click.option("--wait", is_flag=True, help="Wait for the task to complete")
def cli_task_create(
    cmd: tuple[str], environment: str | None, *, queue: str | None, wait: bool
):
    """Create a task.

    Submits a command line task to the cluster (if you have a driver
    configured).

    The command can be any shell command, though for complex ones we
    expect that quoting might become interesting - let us know how you
    get on.  If your command involves options (beginning with a `-`)
    you will need to use `--` to separate the commands to `hipercow`
    from those to your application.  For example

    ```
    hipercow task create -- cowsay -t hello
    ```

    which passes the `-t` argument through to `cowsay`.  We may remove this
    requirement in a future version.

    If you have multiple environments, you can specify the environment
    to run the task in with `--environment`.  We validate the presence
    of this environment at task submission.

    If you use `--wait` then we effectively call `hipercow task wait`
    on your newly created task.  You can use this to simulate a
    blocking task create-and-run type loop, but be aware you might
    wait for a very long time if the cluster is busy.

    """
    resources = None if queue is None else TaskResources(queue=queue)
    task_id = task_create_shell(
        list(cmd), environment=environment, resources=resources
    )
    click.echo(task_id)
    if wait:
        task_wait(task_id)


@task.command("eval", hidden=True)
@click.argument("task_id")
@click.option("--capture/--no-capture", default=False)
def cli_task_eval(task_id: str, *, capture: bool):
    task_eval(task_id, capture=capture)


@task.command("wait")
@click.argument("task_id")
@click.option(
    "--poll",
    default=1,
    type=float,
    help="Time to wait between checking on task (in seconds)",
)
@click.option(
    "--timeout", type=float, help="Time to wait for task before failing"
)
@click.option(
    "--show-log/--no-show-log",
    default=True,
    help="Stream logs to the console, if available?",
)
@click.option(
    "--progress/--no-progress",
    default=True,
    help="Show a progress spinner while waiting?",
)
def cli_task_wait(
    task_id: str,
    *,
    poll: float,
    timeout: float,
    show_log: bool,
    progress: bool,
):
    """Wait for a task to complete."""
    task_wait(
        task_id,
        poll=poll,
        timeout=timeout,
        show_log=show_log,
        progress=progress,
    )


def _process_with_status(with_status: list[str]):
    if not with_status:
        return None
    return reduce(ior, [TaskStatus[i.upper()] for i in with_status])


@cli.group()
def dide():
    """Commands for interacting with the DIDE cluster."""
    pass  # pragma: no cover


@dide.command("authenticate")
@click.argument("action", default="set")
def cli_dide_authenticate(action: str):
    """Interact with DIDE authentication.

    The action can be

    * `set`: Set your username and password (the default)

    * `check`: Check the stored credentials

    * `clear`: Clear any stored credentials

    """
    if action == "set":
        dide_auth.authenticate()
    elif action == "check":
        dide_auth.check()
    elif action == "clear":
        dide_auth.clear()
    else:
        msg = f"No such action '{action}'; must be one of set/check/clear"
        raise Exception(msg)


@dide.command("bootstrap", hidden=True)
@click.argument("target", required=False)
@click.option(
    "--force/--no-force",
    default=False,
    help="Force reinstallation; passed through to pip",
)
@click.option(
    "--verbose/--no-verbose",
    default=True,
    help="Verbose output from pip; default is verbose output",
)
@click.option(
    "--python-version",
    multiple=True,
    help="Python version to update. Multiple copies of this flag allowed",
)
def cli_dide_bootstrap(
    target: str, *, force: bool, verbose: bool, python_version: list[str]
):
    r"""Update the bootstrap.

    You will need `--force` much more often than expcted at present,
    because pip won't always reinstall if only the patch version has
    changed.

    This only works if you have write access to
    `\\wpia-hn\hipercow`.  See the administration guide on the
    hipercow website for details:

    https://mrc-ide.github.io/hipercow-py/administration/

    """
    dide_bootstrap(
        target,
        force=force,
        verbose=verbose,
        python_versions=list(python_version),
    )


@cli.group()
def environment():
    """Interact with environments."""
    pass  # pragma: no cover


@environment.command("list")
def cli_environment_list():
    """List environments."""
    envs = environment_list(root.open_root())
    click.echo("\n".join(envs))


@environment.command("delete")
@click.option("--name")
def cli_environment_delete(name: str):
    """Delete an environment."""
    r = root.open_root()
    environment_delete(name, r)


@environment.command("new")
@click.option("--name", default="default", help="Name of the environment")
@click.option("--engine", default="pip", help="Engine to use")
def cli_environment_new(name: str, engine: str):
    """Create a new environment.

    Note that this does not actually install anything; you will need to use

    ```
    hipercow environment provision
    ```

    to do that, after creation.

    """
    r = root.open_root()
    environment_new(name, engine, r)


@environment.command(
    "provision", context_settings={"ignore_unknown_options": True}
)
@click.option(
    "--name", default="default", help="Name of the environment to provision"
)
@click.argument("cmd", nargs=-1, type=click.UNPROCESSED)
def cli_environment_provision(name: str, cmd: tuple[str]):
    """Provision an environment.

    This will launch a cluster task that installs the packages you
    have requested.  You can pass a command to run here, or use the
    defaults if your project has a well known (and well behaved)
    environment description.

    """
    r = root.open_root()
    provision(name, list(cmd), root=r)


@environment.command("provision-run", hidden=True)
@click.argument("name")
@click.argument("id")
def cli_environment_provision_run(name: str, id: str):
    r = root.open_root()
    provision_run(name, id, r)
