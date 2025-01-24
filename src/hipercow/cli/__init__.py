import click


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
@click.option("-r", "--root", help="Hipercow root directory", type=click.Path())
def status(task_id: str, root=None):
    click.echo(f"Getting task status for '{task_id}'")
