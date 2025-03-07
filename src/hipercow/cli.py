from functools import reduce
from operator import ior

import click

from hipercow import root
from hipercow.configure import configure, show_configuration, unconfigure
from hipercow.dide import auth as dide_auth
from hipercow.driver import list_drivers
from hipercow.environment import (
    environment_delete,
    environment_list,
    environment_new,
)
from hipercow.provision import provision, provision_run
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


@click.group()
@click.version_option()
def cli():
    pass  # pragma: no cover


@cli.command()
@click.argument("path")
def init(path: str):
    root.init(path)


@cli.group()
def driver():
    pass  # pragma: no cover


@driver.command("configure")
@click.argument("name")
def cli_driver_configure(name: str):
    # For now, there are no arguments to drivers so this is easy.
    # However, we will want to be able to pass in generic key/value
    # pairs eventually, and ideally the driver will tell us what these
    # are.
    #
    # Some options to support this might be:
    # https://www.zonca.dev/posts/2022-10-26-click-commandline-class-arguments
    # https://stackoverflow.com/q/36513706 (old)
    #
    # For now, let's just have it on/off.
    r = root.open_root()
    configure(r, name)


@driver.command("unconfigure")
@click.argument("name")
def cli_driver_unconfigure(name: str):
    r = root.open_root()
    unconfigure(r, name)


@driver.command("show")
@click.argument("name", required=False)
def cli_driver_show(name: str | None):
    r = root.open_root()
    show_configuration(r, name)


@driver.command("list")
def cli_driver_list():
    drivers = list_drivers(root.open_root())
    if drivers:
        click.echo("\n".join([str(d) for d in drivers]))
    else:
        click.echo("(none)")


@cli.group()
def task():
    pass  # pragma: no cover


@task.command("status")
@click.argument("task_id")
def cli_task_status(task_id: str):
    r = root.open_root()
    click.echo(task_status(r, task_id))


@task.command("log")
@click.option("--filename", is_flag=True)
@click.argument("task_id")
def cli_task_log(task_id: str, *, filename=False):
    r = root.open_root()
    if filename:
        click.echo(r.path_task_log(task_id))
    else:
        value = task_log(r, task_id)
        if value is not None:
            click.echo(value)


@task.command("list")
@click.option("--with-status", type=str, multiple=True)
def cli_task_list(with_status=None):
    r = root.open_root()
    with_status = _process_with_status(with_status)
    for task_id in task_list(r, with_status=with_status):
        click.echo(task_id)


@task.command("last")
def cli_task_last():
    r = root.open_root()
    task_id = task_last(r)
    if task_id is None:
        # we might set exit code to something nonzero here, but this
        # seems slightly hard...
        pass
    else:
        click.echo(task_id)


@task.command("recent")
@click.option("--limit", type=int)
@click.option("--rebuild", is_flag=True)
def cli_task_recent(limit: int, *, rebuild: bool):
    r = root.open_root()
    if rebuild:
        task_recent_rebuild(r, limit=limit)
    for i in task_recent(r, limit=limit):
        click.echo(i)


@task.command("create")
@click.argument("cmd", nargs=-1)
@click.option("--environment", type=str)
@click.option("--wait", is_flag=True)
def cli_task_create(cmd: tuple[str], environment: str | None, *, wait: bool):
    r = root.open_root()
    task_id = task_create_shell(r, list(cmd), environment=environment)
    click.echo(task_id)
    if wait:
        task_wait(r, task_id)


@task.command("eval")
@click.argument("task_id")
@click.option("--capture/--no-capture", default=False)
def cli_task_eval(task_id: str, *, capture: bool):
    r = root.open_root()
    task_eval(r, task_id, capture=capture)


@task.command("wait")
@click.argument("task_id")
@click.option("--poll", default=1, type=float)
@click.option("--timeout", type=float)
@click.option("--show-log/--no-show-log", default=True)
@click.option("--progress/--no-progress", default=True)
def cli_task_wait(
    task_id: str,
    *,
    poll: float,
    timeout: float,
    show_log: bool,
    progress: bool,
):
    r = root.open_root()
    task_wait(
        r,
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
    pass  # pragma: no cover


@dide.command("authenticate")
@click.argument("action", default="set")
def cli_dide_authenticate(action: str):
    if action == "set":
        dide_auth.authenticate()
    elif action == "check":
        dide_auth.check()
    elif action == "clear":
        dide_auth.clear()
    else:
        msg = f"No such action '{action}'; must be one of set/check/clear"
        raise Exception(msg)


@cli.group()
def environment():
    pass  # pragma: no cover


@environment.command("list")
def cli_environment_list():
    envs = environment_list(root.open_root())
    click.echo("\n".join(envs))


@environment.command("delete")
@click.option("--name")
def cli_environment_delete(name: str):
    r = root.open_root()
    environment_delete(r, name)


@environment.command("new")
@click.option("--name", default="default")
@click.option("--engine", default="pip")
def cli_environment_new(name: str, engine: str):
    r = root.open_root()
    environment_new(r, name, engine)


@environment.command(
    "provision", context_settings={"ignore_unknown_options": True}
)
@click.option("--name", default="default")
@click.argument("cmd", nargs=-1, type=click.UNPROCESSED)
def cli_environment_provision(name: str, cmd: tuple[str]):
    r = root.open_root()
    provision(r, name, list(cmd))


@environment.command("provision-run", hidden=True)
@click.argument("name")
@click.argument("id")
def cli_environment_provision_run(name: str, id: str):
    r = root.open_root()
    provision_run(r, name, id)
