import click

from hipercow import root
from hipercow.task import task_status
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
@click.argument("cmd", nargs=-1)
def create(cmd: tuple[str]):
    r = root.open_root()
    data = {"cmd": list(cmd)}
    task_id = task_create(r, "shell", data, {})
    click.echo(task_id)


@task.command()
@click.argument("task_id")
def eval(task_id: str):
    r = root.open_root()
    task_eval(r, task_id)
