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

If you want to use the current development sources (this will be more useful once we have the development bootstrap up and running: `mrc-6288`) you can do

```command
hatch build
hipercow dide bootstrap --force dist/hipercow-0.0.3-py3-none-any.whl
```

but replacing the version number (`0.0.3`) as required.  The `--force` is required if you are installing the same version number for a second time.

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

For Windows, mamba only works on a physical disk and silently fails when run from a network share such as a home directory. `micromamba.exe` is therefore on each cluster node in the path in `C:\Windows`, so use HPC Cluster Manager on the headnode to copy the exe to all nodes in one go. The bootstrap `micromamba.bat` expects `C:\Windows\micromamba.exe` to exist and simply wraps
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
