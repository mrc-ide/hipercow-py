from functools import reduce
from operator import ior

import click

from hipercow import root
from hipercow.dide import auth as dide_auth
from hipercow.task import TaskStatus, task_list, task_log, task_status
from hipercow.task_create import task_create
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
    data = {"cmd": list(cmd)}
    task_id = task_create(r, "shell", data, {})
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
