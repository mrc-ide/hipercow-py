import click

from hipercow import root
from hipercow.task import task_log, task_status
from hipercow.task_create import task_create
from hipercow.task_eval import task_eval


@click.group()
def cli():
    pass  # pragma: no cover


@cli.command()
@click.argument("path")
def init(path: str):
    root.init(path)


@cli.group()
def task():
    pass  # pragma: no cover


@task.command()
@click.argument("task_id")
def status(task_id: str):
    r = root.open_root()
    click.echo(task_status(r, task_id))


@task.command()
@click.option("--filename", is_flag=True)
@click.argument("task_id")
def log(task_id: str, *, filename=False):
    r = root.open_root()
    if filename:
        click.echo(r.path_task_log(task_id))
    else:
        click.echo(task_log(r, task_id))


@task.command()
@click.argument("cmd", nargs=-1)
def create(cmd: tuple[str]):
    r = root.open_root()
    data = {"cmd": list(cmd)}
    task_id = task_create(r, "shell", data, {})
    click.echo(task_id)


@task.command()
@click.argument("task_id")
@click.option("--capture/--no-capture", default=False)
def eval(task_id: str, *, capture: bool):
    r = root.open_root()
    task_eval(r, task_id, capture=capture)
