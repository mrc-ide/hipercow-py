# Administration

This document is only of interest to people developing `hipercow` and administering the cluster.  If you are a user, none of the commands here are for you.

## Making a release

1. Bump the version number using `hatch version`
2. Commit and push to GitHub, merge the PR
3. Create a new release from the [release page](https://github.com/mrc-ide/hipercow-py/releases)
   * In "Choose a tag" add `v1.2.3` or whatever your version will be - this is created on publish
   * Add the release number into the "Release title"
   * Describe changes (you may want to use the "Generate release notes" button)
4. This will trigger the [release action](https://github.com/mrc-ide/hipercow-py/actions/workflows/release.yml)
5. In a few minutes the new version is available at [its PyPI page](https://pypi.org/project/taskwait/) and can be installed with `pip`

## Updating the bootstrap

In general, we'll want the bootstrap updated from the released versions of the package from PyPI.  In the R version of the project though, we have found it useful to have the concept of a development bootstrap, and the most flexible installation approach would be from disk.

If the version of `hipercow` is on PyPI, you should be able to run, from anywhere:

```command
hipercow dide bootstrap
```

which will update the bootstrap libraries for all supported versions, for both windows and linux. For a specific platform, use the `--platform` argument, or for specific python versions, use as many `--python-version` tags as you like; currently we are supporting versions from `3.10` to `3.13` inclusive.

The cluster nodes do not need python installed, for the bootstrap or to run `hipercow`.  Instead, the bootstrap uses [uv](https://docs.astral.sh/uv/) to download python:

* The first time you bootstrap with a given version of uv (the version installed alongside `hipercow` on your computer), `hipercow dide bootstrap` downloads it from [uv's releases on GitHub](https://github.com/astral-sh/uv/releases), checks it against the published checksum, and saves it on the share as `bootstrap-py-<platform>/uv/<version>/uv` (`uv.exe` on Windows).  You don't need to do anything to install it.
* Each bootstrap job runs `uv run --python <version> bootstrap_install.py`, which makes uv download that version of python into a temporary directory on the node and run the installer with it.
* The installer copies that python into the new installation on the share, and installs `hipercow` into the copy.

The nodes need to be able to reach `releases.astral.sh` (where uv downloads python from) and PyPI.

We copy python, rather than have uv install it straight onto the share, because uv links each python minor version to its latest patch version, and on Windows that link is a junction, which cannot be created on a network share.  The copy has no links outside itself, so each installation is entirely self-contained.

If you want to use the current development sources (this will be more useful once we have the development bootstrap up and running: `mrc-6288`) you can do

```command
hatch build
hipercow dide bootstrap dist/hipercow-0.0.3-py3-none-any.whl
```

but replacing the version number (`0.0.3`) as required.  You can install the same version as often as you like.

### How the bootstrap is laid out

Each run of `hipercow dide bootstrap` submits one job per platform and python version.  Each job creates a brand new installation (a copy of python with `hipercow` installed into it), checks that `hipercow --help` runs, and only then switches jobs over to it.  For each platform the share contains:

```
bootstrap-py-linux/
  uv/0.12.21/uv                      # uv, downloaded by 'hipercow dide bootstrap'
  in/<bootstrap id>/                 # batch files, installer and logs for each run
  python-3.13/
    current                          # name of the installation that jobs use
    installs/20261001120000-1a2b3c4d/  # python and hipercow, one per bootstrap run
    installs/20261101090000-5e6f7a8b/
```

Each installation takes about 200MB, of which python is about 100MB and the copy of uv that `hipercow` uses for environments is about 50MB.

The batch files that `hipercow` writes read `current` and run `installs/<current>/bin/hipercow` (`Scripts\hipercow.exe` on Windows).  Because an installation is never changed once it has been created, jobs that are already running carry on using the installation they started with, and a failed bootstrap leaves the previous installation in place.  We used to use `pipx` to upgrade a single installation in place, which failed on Windows because running jobs hold `hipercow.exe` and compiled libraries open.

The logs from each job are written to `bootstrap-py-<platform>/in/<bootstrap id>/<version>.log` and are printed when the job finishes.  Each installation also contains `hipercow-bootstrap.json`, which records when it was created, what it was installed from, the versions of python and uv, and the versions of all packages.

Each bootstrap gets the latest patch release of each python version, so to update python, run the bootstrap again.

Old installations are deleted by later bootstrap runs once they have been out of use for 30 days, which is long enough for any job that was using them to have finished.  Failed installations are deleted after a day.  To roll back to an earlier installation, write its name (with no trailing newline) into `current`.

Versions of `hipercow` before 0.2.4 run `python-<version>/bin/hipercow` instead, which was installed by `pipx` and is not touched by the bootstrap any more.  Version 0.2.4 and later need `current` to exist, so the first time, run the bootstrap from a wheel built from the release commit (as above) before publishing the release to PyPI.  Once nobody is using these versions, delete the `bin` and `pipx` directories within each `python-<version>` directory, along with `in/pipx.pyz`.

The batch files for Linux jobs still run `module load Python/<version>`.  `hipercow` itself does not use it, but environments made with the `pip` engine use the cluster's python, as do tasks that run `python` in the empty environment, so this stays until nobody relies on those.

## Installing micromamba

Conda environments (`hipercow environment new --engine conda`) are created and run using [micromamba](https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html), a single self-contained executable.  We keep one copy for each platform on the `hipercow` share, next to the bootstrap libraries, and the batch files that `hipercow` writes for each job set the environment variable `HIPERCOW_MICROMAMBA` to point at it:

| Platform | Path on the node | Path on the share |
| --- | --- | --- |
| Linux | `/mnt/cluster/Hipercow/bootstrap-py-linux/micromamba/micromamba` | `\\wpia-hn\hipercow\bootstrap-py-linux\micromamba\micromamba` |
| Windows | `I:\bootstrap-py-windows\micromamba\micromamba.bat` | `\\wpia-hn\hipercow\bootstrap-py-windows\micromamba\micromamba.bat` |

To install or update micromamba for the linux bootstrap, download the binaries from the [micromamba releases](https://github.com/mamba-org/micromamba-releases/releases) page, picking a specific version (these instructions were tested with `2.9.0-0`; you need at least version 2).  With the `hipercow` share mounted (here at `/path/to/hipercow`) run:

```command
VERSION=2.9.0-0
URL=https://github.com/mamba-org/micromamba-releases/releases/download/$VERSION
mkdir -p /path/to/hipercow/bootstrap-py-linux/micromamba
curl -L -o /path/to/hipercow/bootstrap-py-linux/micromamba/micromamba $URL/micromamba-linux-64
chmod +x /path/to/hipercow/bootstrap-py-linux/micromamba/micromamba
```

For Windows, mamba only works on a physical disk and silently fails when run from a network share such as a home directory. `micromamba.exe` is therefore on each cluster node in the path in `C:\Windows`, so use HPC Cluster Manager on the headnode to copy the binary to all nodes in one go. The bootstrap `micromamba.bat` expects `C:\Windows\micromamba.exe` to exist and simply wraps
it sending all arguments.

Check that both platforms can run it, from any directory that is set up for the cluster:

```command
hipercow driver configure dide-linux
hipercow task create --wait -- /mnt/cluster/Hipercow/bootstrap-py-linux/micromamba/micromamba --version
hipercow driver unconfigure dide-linux
hipercow driver configure dide-windows
hipercow task create --wait -- 'I:\bootstrap-py-windows\micromamba\micromamba' --version
```

If the Linux job fails with "Permission denied", the executable bit was not preserved on the share; run the `chmod +x` above from a Linux node.

Finally, check the whole workflow on the Linux cluster, including access to the conda-forge and bioconda channels from the nodes (these are hosted at `conda.anaconda.org`, a different site to PyPI):

```command
hipercow driver unconfigure dide-windows
hipercow driver configure dide-linux
hipercow environment new --name conda-test --engine conda
hipercow environment provision --name conda-test conda install -c bioconda samtools
hipercow task create --wait --environment conda-test -- samtools --version
hipercow environment delete --name conda-test
```

## uv environments

The default environment engine (`hipercow environment new`, or `--engine uv`) uses [uv](https://docs.astral.sh/uv/), which is a dependency of `hipercow`.  Updating the bootstrap installs it alongside `hipercow`, so there is nothing more to copy onto the share.  If the copy from the bootstrap does not work on some nodes (for example, if `uv.exe` cannot be run from the network share, as was the case for `micromamba`), set the environment variable `HIPERCOW_UV` in the batch templates to the location of a working copy.

When an environment is created, `uv` downloads Python into a temporary directory on the node, from `releases.astral.sh`, and `hipercow` copies it into the environment (for the same reason as the bootstrap, above).  Packages come from PyPI.  Check that the nodes can reach both, on each platform:

```command
hipercow driver configure dide-linux
hipercow environment new --name uv-test --python 3.13
hipercow environment provision --name uv-test pip install cowsay
hipercow task create --wait --environment uv-test -- python -c "import sys; print(sys.version)"
hipercow task create --wait --environment uv-test -- cowsay -t moo
hipercow environment delete --name uv-test
```

and repeat with `dide-windows`.
