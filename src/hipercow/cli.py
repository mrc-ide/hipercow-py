from functools import reduce
from operator import ior

import click

from hipercow import root
from hipercow.configure import configure, unconfigure
from hipercow.dide import auth as dide_auth
from hipercow.environment import (
    environment_create,
    environment_list,
    environment_provision,
)
from hipercow.task import TaskStatus, task_list, task_log, task_status
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


@driver.command("list")
def cli_driver_list():
    drivers = root.open_root().list_drivers()
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
        click.echo(task_log(r, task_id))


@task.command("list")
@click.option("--with-status", type=str, multiple=True)
def cli_task_list(with_status=None):
    r = root.open_root()
    with_status = _process_with_status(with_status)
    for task_id in task_list(r, with_status=with_status):
        click.echo(task_id)


@task.command("create")
@click.argument("cmd", nargs=-1)
def cli_task_create(cmd: tuple[str]):
    r = root.open_root()
    task_id = task_create_shell(r, list(cmd))
    click.echo(task_id)


@task.command("eval")
@click.argument("task_id")
@click.option("--capture/--no-capture", default=False)
def cli_task_eval(task_id: str, *, capture: bool):
    r = root.open_root()
    task_eval(r, task_id, capture=capture)


def _process_with_status(with_status: list[str]):
    if not with_status:
        return None
    return reduce(ior, [TaskStatus[i.upper()] for i in with_status])


@cli.group()
def dide():
    pass  # pragma: no cover


@dide.command("authenticate")
@click.option("--clear", is_flag=True)
@click.option("--check", is_flag=True)
def cli_dide_authenticate(clear, check):
    if check:
        dide_auth.check()
    elif clear:
        dide_auth.clear()
    else:
        dide_auth.authenticate()


@cli.group()
def environment():
    pass  # pragma: no cover


@environment.command("list")
def cli_environment_list():
    envs = environment_list(root.open_root())
    click.echo("\n".join(envs))


@environment.command("create")
@click.argument("name")
def cli_environment_create(name: str):
    # Soon, allow args mode, force, clean here
    r = root.open_root()
    environment_create(r, name, "pip")


@environment.command("create")
@click.argument("name")
def cli_environment_provision(name: str):
    r = root.open_root()
    environment_provision(r, name)
