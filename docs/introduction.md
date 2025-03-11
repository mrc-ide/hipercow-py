# Introduction

This section will describe running a simple task on the cluster, using `hipercow`.  We make some assumptions, common to the [R version](https://mrc-ide.github.io/hipercow/):

* You are a member of DIDE at Imperial College London
* You have an account on our cluster; you can check this by logging into [the web portal](https://mrcdata.dide.ic.ac.uk/hpc) with your [DIDE credentials](dide.md#about-our-usernames-and-passwords).  If you cannot log in, please email Wes.
* You are working in a network share that the cluster can see. Ideally this is a **project share** and not your network home directory, as project shares are much faster and more reliable.  See the [DIDE documentation](dide.md#filesystems-and-paths) for more on this topic, including how to configure this on your machine
* You have some Python code that you would like to run on the cluster, which currently works for you locally.
* You are confident executing commands at the command line (bash or similar). If you are not, please do talk with us as we'd be interested in your workflows.

We also make the assumption that you are OK with some rough edges while we develop this system.  Please be prepared to work with us to track down and understand the bugs that you will definitely run into, so that we can make this tool work for people as well as the R package does.

## Project layout

You may have an existing project, or you might be starting from scratch.  We are not at all prescriptive about how you might structure your files, but we will create a directory `hipercow/` at the root of your project, and you must not manually change or delete any file within that directory.  It is safe to mix R and Python `hipercow`s within the same project but at the moment they are [completely unaware of each other's existence despite occupying the same space](https://en.wikipedia.org/wiki/The_City_%26_the_City).  It is likely that you will have a `pyproject.toml` or a `requirements.txt` file at this level, and quite possibly your `.git/` directory.

## Interaction with `hipercow`

If you have [installed `hipercow`](index.md) successfully, then you will be able to run commands with the `hipercow` tool; try running

```console
$ hipercow --help
Usage: hipercow [OPTIONS] COMMAND [ARGS]...

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  dide
  driver
  environment
  init
  task
```

## Authentication

Before starting anything, we should sort out your DIDE credentials.  You need your DIDE username and password - the password might differ from your ICT password, see [our guide to passwords](dide.md#about-our-usernames-and-passwords).  If unsure, you can check by logging into [the web portal](https://mrcdata.dide.ic.ac.uk/hpc).

You can run `hipercow dide authenticate` to store credentials in your system keychain.

```console
$ hipercow dide authenticate
# Please enter your DIDE credentials

We need to know your DIDE username and password in order to log you into
the cluster. This will be shared across all projects on this machine, with
the username and password stored securely in your system keychain. You will
have to run this command again on other computers

Your DIDE password may differ from your Imperial password, and in some
cases your username may also differ. If in doubt, perhaps try logging in
at https://mrcdata.dide.ic.ac.uk/hpc" and use the combination that works
for you there.

DIDE username (default: rfitzjoh) >
Using username 'rfitzjoh'

Password:
I am going to to try and log in with your password now.
If this fails we can always try again

Success! I'm saving these into your keyring now so that we can reuse these
when we need to log into the cluster.
```

At any point you can check credentials by running

```console
$ hipercow dide authenticate check
Fetching credentials
Testing credentials
Success!
```

and you can clear them by running

```console
$ hipercow dide authenticate clear
```

## Initialisation

At the root of your project, run:

```console
$ hipercow init .
Initialised hipercow at .
```

which creates the `hipercow/` directory and enables all other commands.

Because you will want to submit tasks to the DIDE cluster, we need to configure the `dide` driver too:

```console
$ hipercow driver configure dide-windows
Configured hipercow to use 'dide-windows'
```

## Running hello world

Tasks are submitted using `hipercow task create`, followed by any shell command.  In order to make sure that credentials are correct, we recommend submitting a simple task first, like this:

```console
$ hipercow task create --wait echo hello hipercow world
a182aa2b169c2e04aa0a5d27fff1acaa
Waiting......OK
hello hipercow world
```

The `--wait` option should occur before your command and indicates that `hipercow` should wait for the task to complete before returning.  The string printed out (`a182aa2b169c2e04aa0a5d27fff1acaa`) is the "task id" - every task gets one of these and they are unique.

## Running some python code

Running python code requires additional steps; we'll need to set an **environment** for our task to run in, containing any packages that are needed.  If you are in the position where your project does not depend on any packages other than those distributed with python (so no `numpy`, `matplotlib`, or anything else) you can skip this step.

We need to know what packages you need.  There are a couple of ways of configuring this, though probably the easiest is to write a `requirements.txt` file suitable to use with `pip`.  We might have a `requirements.txt` file that contains simply:

```
cowsay
```

indicating that we need that package installed.  Or it could be a bunch of packages and version constraints.

The next step is to indicate that we want a `pip`-based environment; this is the default but this command still needs to be run

```console
$ hipercow environment new
Creating environment 'default' using 'pip'
```

Then we need to install our packages on the cluster, so that tasks that we submit find these packages:

```console
$ hipercow environment provision
Waiting...OK
Actual environment location may have moved due to redirects, links or junctions.
  Requested location: "Q:\cluster\testing\hipercow\py\env\default\contents\venv-windows\Scripts\python.exe"
  Actual location:    "\\qdrive\homes\rfitzjoh\cluster\testing\hipercow\py\env\default\contents\venv-windows\Scripts\python.exe"


  Obtaining dependency information for cowsay from https://files.pythonhosted.org/packages/f1/13/63c0a02c44024ee16f664e0b36eefeb22d54e93531630bd99e237986f534/cowsay-6.1-py3-none-any.whl.metadata
  Downloading cowsay-6.1-py3-none-any.whl.metadata (5.6 kB)
Downloading cowsay-6.1-py3-none-any.whl (25 kB)
Installing collected packages: cowsay


[notice] A new release of pip is available: 24.3.1 -> 25.0.1
[notice] To update, run: python.exe -m pip install --upgrade pip

```

This can take a little while, and we're not really sure why.  And of course a new version of pip is **always** available.

* You will see `Waiting` followed by dots until `OK` while the provisioning task queues.
* The next lines of text are python creating a new empty virtual environment and complaining about paths (this can be ignored)
* Finally, we see the installation of the `cowsay` package

Now, we can submit tasks that use the `cowsay` package:

```console
$ hipercow task create --wait -- cowsay -t "hello hipercow"
fdfaa803fc22c9f4e05fd93247358671
Waiting....OK
  ______________
| hello hipercow |
  ==============
              \
               \
                 ^__^
                 (oo)\_______
                 (__)\       )\/\
                     ||----w |
                     ||     ||
```

The `--` here in the command is (at least currently) required to separate the command between the bits that relate to `hipercow` and the bits for your command (here, the `-t` would make the tool complain).  You also need to use the quotes here around the string to pass to `cowsay` otherwise this will be interpreted as two arguments and not as the argument to `-t`.

You may not see logs produced with this command due to the gap in time between when the task reports as completed and when it finishes writing to disk (or something like that, we're not sure yet).  But you can get the logs

```console
$ hipercow task log fdfaa803fc22c9f4e05fd93247358671
  ______________
| hello hipercow |
  ==============
              \
               \
                 ^__^
                 (oo)\_______
                 (__)\       )\/\
                     ||----w |
                     ||     ||

```

and also get the status of the task:

```console
$ hipercow task status fdfaa803fc22c9f4e05fd93247358671
success
```
