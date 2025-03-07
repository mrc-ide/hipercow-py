# Environments

We use the term "environment" to refer to the context in which a task runs, containing the programs and code it is able to find.  It is not quite the same as [the R `hipercow` concept](https://mrc-ide.github.io/hipercow/articles/environments.html) which considers the execution environment of an R expression, because of the way that Python code is typically run.

There are two key sorts of environments we (aim to) support:

* [Python virtual environments](https://docs.python.org/3/tutorial/venv.html), generally installed via `pip`.  This is effectively a directory of installed python packages, plus some machinery to set the `PATH` environment variable (where the operating system looks for programmes) and the python search path (`sys.path`; where Python looks for packages).
* [Conda environments](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html), generally installed by `conda`, `miniconda`, `mamba` or `micromamba`.  This is a framework popular in bioinformatics and can be used to create a self-consistent installation of a great many tools, isolated from system libraries.

Environments are necessary because we aim to support the minimum useful number of globally installed software on the cluster.  This reduces the number of times you have to wait for someone else to install or update some piece of software that you depend on for your work.

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

## Multiple environments

You can have multiple environments configured within a single `hipercow` root.  This is intended to let you work with a workflow where you need incompatible sets of conda tools, or some jobs with conda and others with pip.  It is not expected that this will be wildly useful to many people and you can generally ignore the existence of this and consider `hipercow environment new` to be simply the way that you plan on configuring a single environment.
