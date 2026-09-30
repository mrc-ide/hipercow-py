# Environments

We use the term "environment" to refer to the context in which a task runs, containing the programs and code it is able to find.  It is not quite the same as [the R `hipercow` concept](https://mrc-ide.github.io/hipercow/articles/environments.html) which considers the execution environment of an R expression, because of the way that Python code is typically run.

There are two key sorts of environments we support:

* [Python virtual environments](https://docs.python.org/3/tutorial/venv.html), generally installed via `pip`.  This is effectively a directory of installed python packages, plus some machinery to set the `PATH` environment variable (where the operating system looks for programs) and the python search path (`sys.path`: where Python looks for packages).
* [Conda environments](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html), generally installed by `conda`, `miniconda`, `mamba` or `micromamba`.  This is a framework popular in bioinformatics and can be used to create a self-consistent installation of a great many tools, isolated from system libraries.  We use `micromamba` to manage these on the cluster (see [below](#provisioning-an-environment-with-conda)).

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

## Provisioning an environment with `conda`

If you need software that is not a Python package (for example bioinformatics tools like `samtools` or `bcftools`, or compiled libraries like GDAL), you probably want a conda environment.  We create and manage these on the cluster using [micromamba](https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html), a small standalone implementation of `conda`, which is already available on the cluster.  You do not need conda installed on your own computer.

Create a conda environment by passing `--engine conda` to `new`:

```command
$ hipercow environment new --engine conda
Creating environment 'default' using 'conda'
```

**The automatic installation** uses an `environment.yml` (or `environment.yaml`) file if your project has one, running `conda install --file environment.yml` on the cluster:

```command
$ hipercow environment provision
```

Any `name:` or `prefix:` in the file is ignored, as `hipercow` decides where the environment lives.  A `pip:` section within the file is supported.

**The manual installation** takes a `conda` command.  You can write `conda`, `mamba` or `micromamba` (these all mean the same thing here), followed by one of `install`, `update`, `remove` (or `uninstall`) or `clean`:

```command
$ hipercow environment provision conda install -c bioconda samtools
```

We add `--yes` and the location of the environment for you.  Do not pass `--name`/`-n` or `--prefix`/`-p`.

You can also install packages from PyPI into a conda environment with `pip`, once you have installed `python` and `pip` into it:

```command
$ hipercow environment provision conda install python=3.12 pip
$ hipercow environment provision pip install cowsay
```

### Channels

Packages come from [conda-forge](https://conda-forge.org/) by default.  Channels that you add with `-c` are *added* to conda-forge rather than replacing it, so `-c bioconda` works as [the bioconda documentation](https://bioconda.github.io/) expects.

Your personal `.condarc` file is **not** used when provisioning.  This keeps environments on the cluster reproducible, and avoids accidentally mixing in Anaconda's `defaults` channel, which does not mix well with conda-forge.  If you really need to change the configuration, edit the `.mambarc` file in `hipercow/py/env/<name>/contents/mamba-<platform>/` after creating the environment.

### Linux or Windows?

Many conda packages, including everything on bioconda, are only built for Linux and macOS.  For example, `samtools` cannot be installed on Windows.  If you use conda for bioinformatics, use the Linux cluster:

```command
$ hipercow driver configure dide-linux
```

Environments are created separately for each platform, so if you change driver you will need to provision again.

### Running tasks in a conda environment

Tasks run with the environment activated, so everything you installed can be found:

```command
$ hipercow task create -- samtools view -c data/reads.bam
```

The `--` stops `hipercow` from trying to interpret any options (like `-c`) that are meant for your program.

### Disk space

Conda environments can be large, and they live on the network share alongside your project.  `micromamba` also keeps a cache of downloaded packages, which may be as big as the environment itself.  Once your environment is working, you can delete this cache with:

```command
$ hipercow environment provision conda clean --all
```

This does not affect the installed environment, though later installations will need to download packages again.

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
* mixing `pip`- and `conda`-based environments in one project
