# Environments

We use the term "environment" to refer to the context in which a task runs, containing the programs and code it is able to find.  It is not quite the same as [the R `hipercow` concept](https://mrc-ide.github.io/hipercow/articles/environments.html) which considers the execution environment of an R expression, because of the way that Python code is typically run.

There are two key sorts of environments we (aim to) support:

* [Python virtual environments](https://docs.python.org/3/tutorial/venv.html), generally installed via `pip`.  This is effectively a directory of installed python packages, plus some machinery to set the `PATH` environment variable (where the operating system looks for programs) and the python search path (`sys.path`: where Python looks for packages).
* [Conda environments](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html), generally installed by `conda`, `miniconda`, `mamba` or `micromamba`.  This is a framework popular in bioinformatics and can be used to create a self-consistent installation of a great many tools, isolated from system libraries.

Environments are necessary because we aim to keep globally installed software on the cluster to a minimum.  This reduces the number of times you have to wait for someone else to install or update some piece of software that you depend on for your work.

## In a nutshell

The basic approach for working with environments is:

1. Tell `hipercow` the sort of environment you want to work with, and what it is called
2. Install things into that environment (this is launched from your computer but runs on the cluster)
3. Run a task that uses your environment

```
$ hipercow environment new
$ hipercow environment provision
$ hipercow task create mytool
```

You must have a driver configured (e.g., by running `hipercow driver configure dide`) in order to provision an environment.

## Default environments

You always have an environment called `empty`, which contains nothing.  This can run shell commands on the cluster, but without referencing any interesting software.  In the unlikely event that you have a python package that does not need any non-default packages this is all you need.  You cannot install anything else into this environment.

```command
$ hipercow environment list
empty
```

You can initialise a more interesting environment using `new`, this will by default initialise the environment `default` using the `pip` engine:

```command
$ hipercow environment new
Creating environment 'default' using 'pip'
```

## Provisioning an environment with `pip`

To provision an environment, use `hipercow environment provision`; this runs on the cluster and installs the packages you need to run your tasks.  This is needed because the cluster cannot see the packages you have installed locally, and the cluster nodes might be a different operating system type to your computer anyway.  You can install packages automatically or manually.

**The automatic installation** will get better over time, but we hope this is enough to get at least some people going.  The rules are:

* If `pyproject.toml` exists, we try and install the project using `pip install .`
* If `requirements.txt` exists, we try and install from that using `pip install -r requirements.txt`
* Otherwise we error.

If your project has either `pyproject.toml` or `requirements.txt`, hopefully you can just run

```command
$ hipercow environment provision
```

which will set up the `default` environment with the packages that you need.

There are lots of ways we could improve this in future, for example:

* Allow switching the environment from `pyproject.toml`
* Selection of groups of optional packages to install
* Multiple installation steps
* Attempt to install a project in editable mode

Please let us know if you have ideas on how this could be improved.

**The manual installation** is very simple; provide a command that calls `pip` and we'll run it on the cluster.

For example, suppose you need a couple of extra packages:

```command
$ hipercow environment provision pip install cowsay fortune-python
```

and now both the `cowsay` and `fortune` packages (and command line interfaces) are available.

## Multiple environments

You can have multiple environments configured within a single `hipercow` root.  This is intended to let you work with a workflow where you need incompatible sets of conda tools, or some jobs with conda and others with pip.  It is not expected that this will be wildly useful to many people and you can generally ignore the existence of this and consider `hipercow environment new` to be simply the way that you plan on configuring a single environment.

You can run

```command
$ hipercow environment create --name dev
```

to create a new `dev` environment.  You can provision this the same way as above, but passing `--name dev` through to `provision`

```command
$ hipercow environment provision --name dev pip install <packages...>
```

and then when submitting tasks use the `--environment` option to select the environment:

```command
$ hipercow task create --environment dev <your command here>
```

Possible use cases of this functionality are:

* trying out a different version of a package side-by-side with a previous installation to compare results
* installing an update without disrupting tasks that are already queued up
* mixing `pip`- and `conda`-based environments in one project (once the latter are supported)
