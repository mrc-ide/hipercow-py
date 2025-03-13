# Using TLO

These instructions are for using the [Thanzi la Onse model](https://github.com/UCL/TLOmodel) model on the DIDE cluster with hipercow.  We'll probably update some of the [`TLOmodel` wiki](https://github.com/UCL/TLOmodel/wiki) once things stabilise and then we can perhaps point there as a source of truth.

**The current state of play**: We can currently run a simple copy of the model on the cluster, running on Python 3.11 under Windows.  None of the Azure workflows are supported.

Minimal instructions, within a clone of [`TLOmodel`](https://github.com/UCL/TLOmodel).

First set up a hipercow root and configure it to use Python 3.11 on the DIDE Windows cluster:

```console
hipercow init
hipercow driver configure dide-windows --python-version=3.11
hipercow driver show dide-windows
```

Install the dependencies and the model itself into a virtual environment on the cluster:

```console
hipercow environment new
hipercow environment provision -- pip install --verbose -r requirements/dev.txt
hipercow environment provision -- pip install --verbose .
```

On the home drive, installation takes 200-300s for the development requirements and and 66s for the package itself.  The requirements installation will appear to pause with no output for quite a while.

Optionally, confirm that things work:

```console
hipercow task create --wait -- tlo --help
```

You can submit tasks with the `tlo` command to run a scenario.  For example:

```console
hipercow task create tlo scenario-run src/scripts/dev/scenarios/cluster-run.py
```

After which you can use `hipercow task wait`, `hipercow task log` and `hipercow task status` to keep an eye on your task.  If you have many tasks to submit, you might need to use a loop in bash or similar.
