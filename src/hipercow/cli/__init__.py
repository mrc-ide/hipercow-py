import click

from hipercow.root import open_root
from hipercow.task import task_status
from hipercow.task_create import task_create


@click.group()
def cli():
    pass

@cli.command()
@click.argument("path")
def init(path: str):
    click.echo(f"Initialise hipercow at '{path}'")


@cli.group()
def task():
    pass


@task.command()
@click.argument("task_id", type=str)
def status(task_id: str):
    root = open_root()
    click.echo(task_status(root, task_id))


@task.command()
@click.argument("cmd", nargs=-1)
def create(cmd: str):
    root = open_root()
    envvars = {}
    task_id = task_create(root, "shell", list(cmd), envvars)
    click.echo(task_id)
