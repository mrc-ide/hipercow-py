# uv: default environments, and no Python needed on the cluster

Branch: `conda-environments` (not yet committed or pushed)

## Summary

hipercow used to need Python installed on the cluster in three places:

1. **The bootstrap** installed hipercow with the cluster's Python (`module load Python/…` on Linux, `set_python_*` on Windows).
2. **Every job** ran hipercow from a venv that pointed back at that same cluster Python.
3. **User environments** (the `pip` engine) were built with `python -m venv` from the cluster's Python. So users could only have the Python versions the admin had bootstrapped (3.10–3.13).

This change removes the need for all three, using [uv](https://docs.astral.sh/uv/):

* **Part 1: a `uv` environment engine, now the default.** Users choose any Python version (`hipercow environment new --python 3.14`), and uv downloads it into the environment. `pip install …` commands keep working, and projects with a `uv.lock` are installed with `uv sync --locked`.
* **Part 2: a Python-free bootstrap.** `hipercow dide bootstrap` puts a uv binary on the share. Each bootstrap job uses it to download Python, and installs hipercow into a self-contained copy of that Python on the share. Jobs run that copy, so **the nodes need no Python at all**.

Both parts rely on the same finding. **On Windows, uv can't install Python onto a network share**: it links each minor version with an NTFS junction, which Windows refuses to create on network drives. So in both cases uv downloads Python into a temporary directory on the node's local disk, and hipercow copies it onto the share as a plain directory. Linux uses the same code, which is how it was tested.

What's still there:
* The `pip` engine still exists (`--engine pip`), and existing `pip` environments keep working.
* The Linux job scripts still run `module load Python/…`, for those `pip` environments and for tasks that run `python` in the `empty` environment. hipercow itself doesn't use it.

The bootstrap builds on the rewrite already in the working tree: a fresh installation per run, a `current` pointer, a smoke test before switching, and pruning of old installations. All of that is unchanged. What changed is where Python comes from, and that each installation is now a self-contained copy of Python rather than a venv.

---

# Part 1: uv environments

## Worked example: what a user does

This follows a researcher fitting a model with `numpy` and `scipy`. They want Python 3.14, which isn't installed on the cluster or on their own computer.

> **Where the output comes from.** The output shown is real. It was captured on a Linux workstation with hipercow's `example` driver, which runs the same provisioning and task code locally instead of on a cluster node. `HOME` pointed at an empty directory. The workstation had Python 3.10 and 3.11, but not 3.12, 3.13 or 3.14. Things that couldn't be run without the cluster:
>
> * the DIDE login and driver setup in step 2;
> * `--wait`: each task was run with `hipercow task eval` and its log printed instead;
> * Windows nodes.
>
> On the cluster you'd also see job-submission messages, the provisioning log streaming to your terminal, and a progress spinner. The task output is the same. Part 2 describes a test that runs the real cluster job scripts.

### 1. The project

```text
growth-model/
├── requirements.txt        numpy
└── scripts/
    └── fit.py
```

```python
import sys

import numpy as np

rng = np.random.default_rng(1)
x = np.arange(10)
y = 2.5 * x + rng.normal(size=10)
slope, intercept = np.polyfit(x, y, 1)
print(f"Python {sys.version.split()[0]}, numpy {np.__version__}")
print(f"slope={slope:.2f} intercept={intercept:.2f}")
```

### 2. One-off setup

This step hasn't changed:

```shell
hipercow dide authenticate          # once per computer
cd /path/to/share/growth-model      # or Q:\growth-model on Windows
hipercow init .
hipercow driver configure dide-linux
```

### 3. Create the environment, choosing Python

```console
$ hipercow environment new --python 3.14
i Creating environment 'default' using 'uv' with Python 3.14

$ cat hipercow/py/env/default/config
{"engine":"uv","python":"3.14"}
```

Without `--python`, uv takes the version from the project, in this order:

1. `.python-version`
2. `requires-python` in `pyproject.toml`
3. the latest stable release (3.14.7 at the time of testing)

### 4. Provision

```console
$ hipercow environment provision
```

With no command given, hipercow finds `requirements.txt` and records `pip install -r requirements.txt`.

On the node, uv first chooses Python and downloads it into a temporary directory, by making a throwaway venv there. hipercow then copies that Python into the environment, and builds the real venv from the copy. The provisioning log:

```text
Downloading cpython-3.14.7-linux-x86_64-gnu (download) (34.6MiB)
 Downloaded cpython-3.14.7-linux-x86_64-gnu (download)
Using CPython 3.14.7
Creating virtual environment at: /tmp/tmpXXXX/venv
Activate with: source /tmp/tmpXXXX/venv/bin/activate
Using CPython 3.14.7 interpreter at: hipercow/py/env/default/contents/uv-linux/python/bin/python3
Creating virtual environment at: hipercow/py/env/default/contents/venv-linux
Activate with: source hipercow/py/env/default/contents/venv-linux/bin/activate
Using Python 3.14.7 environment at: hipercow/py/env/default/contents/venv-linux
Resolved 1 package in 124ms
Downloading numpy (15.9MiB)
 Downloaded numpy
Prepared 1 package in 406ms
Installed 1 package in 14ms
 + numpy==2.5.3
```

This took a few seconds on the workstation. On the cluster it will depend on the share and the nodes' network.

### 5. Run jobs

```console
$ hipercow task create -- python scripts/fit.py
bca9c0a26bbc1fa8e29e4643fb999d8f

$ hipercow task status bca9c0a26bbc1fa8e29e4643fb999d8f
success

$ hipercow task log bca9c0a26bbc1fa8e29e4643fb999d8f
Python 3.14.7, numpy 2.5.3
slope=2.50 intercept=0.24
```

### 6. Add packages later

```console
$ hipercow environment provision pip install scipy
```

```text
Using Python 3.14.7 environment at: hipercow/py/env/default/contents/venv-linux
Resolved 2 packages in 132ms
Downloading scipy (33.7MiB)
 Downloaded scipy
Prepared 1 package in 852ms
Installed 1 package in 23ms
 + scipy==1.18.1
```

`pip list`, `pip show`, `pip freeze`, `pip uninstall` (with or without `-y`), `pip tree` and `pip check` all work too. Their output goes to the provisioning log.

### 7. Projects managed with uv

If the project has a `uv.lock`, provisioning installs exactly what it lists. This project has `requires-python = ">=3.11"`, `dependencies = ["cowsay"]` and a `.python-version` containing `3.13`:

```console
$ uv lock                               # on your own computer, as usual
$ hipercow environment new
i Creating environment 'default' using 'uv'

$ hipercow environment provision
```

The recorded command is `["uv", "sync", "--locked"]`, and the log shows Python 3.13.15 coming from `.python-version`. uv installs into hipercow's environment, not into a `.venv` in the project: no `.venv` was created.

Editing `pyproject.toml` without re-locking makes provisioning fail, with uv's own explanation in the log:

```text
error: The lockfile at `uv.lock` needs to be updated, but `--locked` was provided.

hint: To update the lockfile, run `uv lock`.
```

After `uv lock`, provisioning again installed just the four new packages. `uv sync` makes the environment match the lock exactly. In testing, a package added afterwards with `pip install six` was removed by the next `uv sync --locked`.

### 8. Several Python versions side by side

```console
$ hipercow environment new --name py312 --python 3.12
$ hipercow environment provision --name py312
$ hipercow environment new --name legacy --engine pip
$ hipercow environment provision --name legacy pip install cowsay
```

The same `python -c 'import sys; print(sys.version.split()[0], sys.base_prefix)'` task, run in each environment:

```text
default: 3.13.15 hipercow/py/env/default/contents/uv-linux/python
py312:   3.12.14 hipercow/py/env/py312/contents/uv-linux/python
legacy:  3.11.8  /home/athapar/miniconda3
```

`--python 3.12` wins over the project's `.python-version` (3.13). Each uv environment runs its own copy of Python. The `pip` environment uses whatever Python the machine has.

### 9. When things go wrong

Mistakes in the command are caught on the user's computer, before any job is submitted:

```console
$ hipercow environment provision pip install --python 3.12 pandas
Error: Don't use '--python' when provisioning; hipercow manages the location of the environment (set the Python version with 'hipercow environment new --python')

$ hipercow environment provision pip download pandas
Error: Expected 'pip' to be followed by one of 'check', 'freeze', 'install', 'list', 'show', 'sync', 'tree', 'uninstall'

$ hipercow environment provision conda install samtools
Error: Expected first element of 'cmd' to be 'pip' or 'uv'

$ hipercow environment new --name old --engine pip --python 3.12
Error: Choosing a Python version is only supported by the 'uv' engine
```

A package that doesn't exist fails during provisioning, and the log says why:

```text
error: No solution found when resolving dependencies
  cause: Because numpyy was not found in the package registry and you require numpyy, we can conclude that your requirements are unsatisfiable.
```

### 10. Housekeeping

```console
$ hipercow environment provision uv cache clean
$ hipercow environment delete --name py312
```

The cache is usually small, because uv hard-links packages from the cache into the venv (2.1 MiB freed in testing).

## How a uv environment works

```text
your machine                              cluster node (Linux or Windows)
------------                              -------------------------------
hipercow environment new --python 3.14
  writes {"engine":"uv","python":"3.14"}

hipercow environment provision ...  --->  provision run.sh / run.bat
  Uv.check_args() validates cmd             hipercow environment provision-run
  writes provision/<id>/data                  Uv.create()        (first time only)
  submits the job                               uv venv <tmp>/venv        (downloads Python to <tmp>)
                                                copy Python -> contents/uv-<platform>/python
                                                uv venv --python <copy> <venv>
                                              Uv.provision()
                                                uv pip install --python <venv> ...
                                                or: uv sync --locked

hipercow task create ...  ------------->  task_run.sh / task_run.bat
                                            hipercow task eval
                                              Uv.run() (= Pip.run)
                                                VIRTUAL_ENV=<venv>, PATH=<venv>/bin:...
```

The throwaway venv in step one lets uv choose the version exactly as it would for the real environment: `--python`, then `.python-version`, then `requires-python`.

### Layout within the project

```text
<project>/hipercow/py/env/<name>/
  config                   {"engine": "uv", "python": "3.14"}   ("python" only if given)
  provision/<id>/          data, log, result, run.sh or run.bat (as for pip)
  contents/
    venv-linux/            the virtual environment
    uv-linux/
      python/              this environment's copy of Python (a plain directory, ~110 MB)
      cache/               uv's cache (can be emptied with `uv cache clean`)
    venv-windows/          only if provisioned from Windows nodes
    uv-windows/
```

### Environment variables set by the engine (for `uv` commands only)

While creating the environment (the throwaway venv):

| Variable | Value | Why |
| --- | --- | --- |
| `UV_PYTHON_INSTALL_DIR` | a temporary directory on the node | Download Python to local disk, where Windows can create uv's junction. Never to the share or the home directory. |
| `UV_MANAGED_PYTHON` | `1` | Never use a Python installed on the system. Environment variables beat a user's `uv.toml` (verified). |
| `UV_PYTHON` | the `--python` value, if given | Takes priority over `.python-version`. |

For every command afterwards:

| Variable | Value | Why |
| --- | --- | --- |
| `UV_PYTHON` | absolute path to the environment's copy of Python | Pins every command, including `uv sync`, to that copy. |
| `UV_PYTHON_DOWNLOADS` | `never` | uv never downloads another Python, for example into the home directory. |
| `UV_PROJECT_ENVIRONMENT` | `contents/venv-<platform>` | `uv sync` installs into hipercow's venv instead of creating `.venv` in the project. |
| `UV_CACHE_DIR` | `contents/uv-<platform>/cache` | Keeps the cache with the environment, so `environment delete` removes it. |

Tasks run with only `VIRTUAL_ENV` and `PATH` set, exactly as for `pip`.

---

# Part 2: bootstrapping hipercow without the cluster's Python

## What used to happen

```text
bootstrap job:  module load Python/3.12   (Windows: call set_python_312_64)
                python bootstrap_install.py ... → python -m venv installs/<name>
                                                 → pip install hipercow

every job:      module load Python/3.12
                installs/<name>/bin/hipercow     → venv's python → the cluster's Python
```

A venv isn't a full Python: its `bin/python` points back at the Python it was made from. So the cluster's Python was needed both to install hipercow and to run every job.

## What happens now

```text
admin's machine                         bootstrap job (any node, no Python)
---------------                         -----------------------------------
hipercow dide bootstrap
  downloads uv 0.12.21 from GitHub,       export UV_PYTHON_INSTALL_DIR=$(mktemp -d)   # local disk
  checks its sha256, saves it at          uv run --python 3.13 bootstrap_install.py ...
  bootstrap-py-<platform>/uv/0.12.21/       uv downloads Python 3.13 into the temp dir and runs:
  (only if not already there)               copy that Python  → python-3.13/installs/<name>/
  submits one job per version/platform      uv pip install --python <copy> hipercow
                                            <copy>/bin/hipercow --help                # smoke test
                                            write 'current'                           # switch jobs over
                                          rm -rf the temp dir

every job:   installs/<current>/bin/hipercow  → installs/<current>/bin/python3   (all on the share)
```

Each installation is a complete Python with hipercow and its dependencies installed into it. There's no venv, and nothing links outside the directory. The other person's design is otherwise unchanged:
* jobs that are already running keep their installation;
* a failed bootstrap leaves `current` alone;
* old installations are pruned after 30 days, which now deletes their Python with them.

### Layout on the share

```text
bootstrap-py-linux/                        (bootstrap-py-windows/ is the same)
  uv/0.12.21/uv                            uv itself (uv.exe on Windows); one directory per version, never replaced
  in/<bootstrap id>/                       job scripts, bootstrap_install.py, wheel (if any) and logs
  python-3.13/
    current                                name of the installation that jobs use
    installs/20261001152557-0123abcd/      Python 3.13.15 + hipercow + uv (~200 MB)
      bin/python3 -> python3.13            relative links within the copy only (none on Windows)
      bin/hipercow
      bin/uv                               the uv that user environments use
      hipercow-bootstrap.json              versions of hipercow, Python, uv and every package
```

### The Linux bootstrap job, as generated

```bash
source /etc/profile

# No python is needed on the node: uv downloads it into a temporary
# directory here and bootstrap_install.py copies it onto the share.
export UV_PYTHON_INSTALL_DIR=$(mktemp -d)
export UV_MANAGED_PYTHON=1
export UV_NO_CACHE=1
export UV_NO_CONFIG=1
export PYTHONUNBUFFERED=1

/mnt/cluster/Hipercow/bootstrap-py-linux/uv/0.12.21/uv run --no-project --python 3.13 \
  .../in/<id>/bootstrap_install.py --root ... --python-version 3.13 --name <name> \
  --uv /mnt/cluster/Hipercow/bootstrap-py-linux/uv/0.12.21/uv hipercow > .../3.13.log 2>&1

rm -rf $UV_PYTHON_INSTALL_DIR
```

The Windows job is the same, with `%TEMP%\hipercow-bootstrap-<id>-<version>` as the temporary directory. `UV_NO_CONFIG` stops a `uv.toml` belonging to the admin, or left on the node, from changing what gets installed. `UV_NO_CACHE` keeps nothing on the share or in the home directory beyond the installation itself.

### A real bootstrap log

This is from the end-to-end test below. The share is a temporary directory, and the job ran with a `PATH` containing no Python:

```text
Downloading cpython-3.13.15-linux-x86_64-gnu (download) (33.4MiB)
 Downloaded cpython-3.13.15-linux-x86_64-gnu (download)
There is no current installation
Installing '<share>/bootstrap-py-linux/in/0123abcd/hipercow-0.2.4-py3-none-any.whl' into '<share>/bootstrap-py-linux/python-3.13/installs/20261001152557-0123abcd'
Copying python from '/tmp/tmp.0V8bwin1Da/cpython-3.13.15-linux-x86_64-gnu'
> <share>/bootstrap-py-linux/uv/0.12.21/uv pip install --python <share>/bootstrap-py-linux/python-3.13/installs/20261001152557-0123abcd/bin/python3 <share>/bootstrap-py-linux/in/0123abcd/hipercow-0.2.4-py3-none-any.whl
Resolved 32 packages in 208ms
...
Installed 32 packages in 8ms
> <share>/bootstrap-py-linux/python-3.13/installs/20261001152557-0123abcd/bin/hipercow --help
...
hipercow 0.2.4 is now current for python 3.13
```

### The task job scripts

The task and provisioning scripts only needed one change: the share path is now a template variable, `${bootstrap_root}`, with the same value as before, so that a test can point it at a fake share. They still read `current` and run `installs/<current>/bin/hipercow`, as in the other person's rewrite. That's now a self-contained Python, so on Windows nothing is needed on the node, and on Linux `module load Python` no longer matters to hipercow. That line stays, with a comment, for `pip` environments.

---

# Why copy Python, instead of letting uv install it on the share

From uv's source (`crates/uv-python/src/managed.rs` and `crates/uv-fs/src/lib.rs`):

* After installing any Python, in both `uv python install` and automatic downloads, uv calls `ensure_minor_version_link()`. This links, for example, `cpython-3.13-…` to `cpython-3.13.15-…`.
* On Windows that link is an **NTFS junction**, created by `replace_with_junction`. uv only uses a symbolic link instead when it's running under Wine.
* If creating the link fails, **uv returns an error**. No setting turns the link off.
* Windows only creates junctions on local volumes. Trying one on a network drive gives "Local volumes are required to complete the operation".

So pointing `UV_PYTHON_INSTALL_DIR` at the share would very likely make every Windows bootstrap job and every Windows uv environment fail.

Instead, the job that does the install (a bootstrap job, or the provisioning job for a uv environment) works in two steps. This happens once per install, on whichever single node runs that job, not on every compute node:

1. uv downloads Python into a temporary directory on that node's local disk. The disk is local, so creating the junction works.
2. The job copies that Python onto the share: to `bootstrap-py-<platform>/python-<version>/installs/<id>/` for bootstrap, or to `contents/uv-<platform>/python/` for an environment. The temporary directory is then deleted, so nothing is left on the node.

After that, every task on every node runs Python from the copy on the share. Nothing is downloaded again, and the nodes don't need Python installed. This works because the Python builds uv downloads ([python-build-standalone](https://github.com/astral-sh/python-build-standalone)) still run after being moved (verified: the copy on the share ran after the temporary directory was deleted).

Linux would cope without this (CIFS supports symlinks), but using the same code everywhere is what let the Windows path be tested here.

# Why uv, and not the alternatives

| Option | Verdict |
| --- | --- |
| **uv, Python copied onto the share** (chosen) | Any Python version, with no admin work per version and no Python on the nodes. The same code on Linux and Windows. |
| Keep the cluster's Python (status quo) | Every version must be installed on every node or as a module, and users can only have those versions. |
| uv with `UV_PYTHON_INSTALL_DIR` on the share | Simpler, but very likely fails on Windows (junctions, above). |
| Admin installs Python onto the share by hand | Ongoing work every time a version changes, and the job scripts still have to find it. |
| conda for Python | Heavier and slower, and mixes conda and PyPI packages. Better kept for non-Python tools. |

---

# Changes, file by file

### Part 1: uv environments

* **New: `src/hipercow/environment_engines/uv.py`.** `Uv(Pip)` reuses `Pip`'s venv layout and `run()`.
  * `create()`: a throwaway `uv venv` in a temporary directory (downloading Python), then a copy into `contents/uv-<platform>/python/`, then `uv venv --python <copy> <venv>`. The new `path_python()` gives the copy's executable.
  * `check_args()`:
    * accepts `pip …`, `uv pip …`, `uv sync …` and `uv cache …`;
    * `pip` must be followed by a subcommand `uv pip` supports;
    * `--python`, `-p`, `--system`, `--prefix` and `--target` are refused;
    * with no command it picks `uv.lock` → `uv sync --locked`, then `pyproject.toml` → `pip install .`, then `requirements.txt` → `pip install -r requirements.txt`.
  * `provision()`: `pip …` becomes `uv pip … --python <venv>`.
  * `_uv()`: uses `$HIPERCOW_UV` if set, otherwise `uv.find_uv_bin()`, which is the uv installed next to hipercow.
* **`src/hipercow/environment.py`:**
  * the config gains an optional `python` field, written only when given, so `pip` and `conda` configs are byte-for-byte unchanged;
  * `environment_new(..., *, python=None)` accepts `engine="uv"` and rejects `python` for other engines;
  * `environment_engine()` returns `Uv`.
* **`src/hipercow/environment_engines/__init__.py`:** exports `Uv`.
* **`src/hipercow/cli.py`:** `environment new` now defaults to `--engine uv`, and gains `--python`.
* **`pyproject.toml`:** adds the dependency `uv>=0.8`.

### Part 2: bootstrap

* **New: `src/hipercow/dide/bootstrap_uv.py`.** `bootstrap_uv(mount, platform, version)` downloads `uv-x86_64-unknown-linux-gnu.tar.gz` or `uv-x86_64-pc-windows-msvc.zip` from `github.com/astral-sh/uv/releases` and checks it against the published `.sha256`. It then writes the binary to `bootstrap-py-<platform>/uv/<version>/` through a temporary file and a rename, and does nothing if it's already there. The version is the uv installed alongside hipercow on the admin's machine.
* **`src/hipercow/dide/bootstrap_install.py`:**
  * a new `--uv` argument;
  * `install()` now calls `copy_python(sys.base_prefix, dest)`, which copies the Python and removes uv's `EXTERNALLY-MANAGED` marker from the copy;
  * it then runs `uv pip install --python <copy>`, the smoke test, and `uv pip freeze`;
  * the metadata records the copy's Python and the version of uv;
  * `python_path()` and `scripts_path()` replace `venv_bin()`, because Python sits at the top of a Windows installation, not in `Scripts\`;
  * the docstring explains the approach. It's still standard library only.
* **`src/hipercow/dide/bootstrap.py`:** now holds everything that submits bootstrap jobs. **`bootstrap_linux.py` and `bootstrap_windows.py` are deleted**: they were near-identical copies differing only in template, separators, queue and submission path.
  * `BOOTSTRAP_SH` and `BOOTSTRAP_BAT` are the new job scripts shown above, with no `module load Python` or `call set_python_*`.
  * `_bootstrap_script(platform, …)` fills in either template. It takes an optional `root`, used by the end-to-end test.
  * `_bootstrap_submit()` writes and submits the job for either platform.
  * `bootstrap()` calls `bootstrap_uv()` for each platform before submitting, and passes the uv version to the jobs.
* **`src/hipercow/dide/batch_linux.py` and `batch_windows.py`:** `${bootstrap_root}` replaces the hard-coded share path in all four job templates, with the same values as before (`BOOTSTRAP_ROOT_LINUX`, `BOOTSTRAP_ROOT_WINDOWS`). There's also a comment on why `module load Python` stays.

### Cleanup of code made obsolete by this change

* The two platform-specific bootstrap modules were merged into `bootstrap.py` (above).
* `hipercow.util.PYTHON_VERSIONS` is now the single list of supported Python versions, used by `check_python_version()` and the bootstrap. It replaces a duplicate list marked "NOTE: duplicates list in hipercow/util.py".
* `bootstrap_install.py` no longer has `from __future__ import annotations`. That was there so "an older python" could report a version mismatch, but uv now runs the script with exactly the requested version.
* A stale comment in `bootstrap()` about cleaning up with `shutil.rmtree(path)`, for a variable that no longer existed, now says that the `in/<id>` directories are kept for debugging.
* Kept on purpose: the version check in `bootstrap_install.py` (a cheap guard against mismatched arguments), the transition notes for pipx-era installs in `docs/administration.md` (still needed to roll out), and `module load Python` (above).
* **`src/hipercow/cli.py`:** the `dide bootstrap` help explains that the cluster needs no Python.

### Tests

| File | What |
| --- | --- |
| `tests/test_environment_uv.py` (new) | 11 unit tests (mocked `subprocess.run`): paths, both sets of environment variables, the three steps of `create()` (download to a temporary directory, copy, venv from the copy; the copy exists and the temporary directory is gone), command translation, `run()`, the automatic defaults, argument checks, and `HIPERCOW_UV`. |
| `tests/zzz/test_environment_uv.py` (new, `slow`) | Real uv environments: `--python 3.13` with `requirements.txt`; and a `uv.lock` project with `.python-version` 3.12. Checks that tasks run on the environment's copy of Python, and that failures are reported. |
| `tests/dide/test_bootstrap_uv.py` (new) | 6 tests (HTTP mocked with `responses`): Linux and Windows archives, the executable bit, no second download, checksum mismatch refused with nothing written, an archive without `uv`. |
| `tests/dide/test_bootstrap_install.py` | Updated for `--uv` and the uv commands. New: `copy_python` copies the tree, keeps relative symlinks and removes the marker from the copy only; and the Windows and Linux paths. |
| `tests/dide/test_bootstrap.py` | Updated job script contents: `uv run --no-project --python …`, no `module`/`set_python`, `UV_MANAGED_PYTHON=1`. `bootstrap()` downloads uv once per platform and passes the version on. The test of the removed duplicate version list is gone. |
| `tests/zzz/test_bootstrap_dide.py` (new, `slow`) | **The full flow on Linux, with no Python on the `PATH`.** It downloads the real uv release, builds a wheel from this source tree, and runs the generated bootstrap `.sh` with bash against a fake share. It then runs the generated provisioning and task `.sh` scripts with the installed hipercow: a uv environment with Python 3.12, plus `cowsay` and `python` tasks. Finally it checks that `HOME` is still empty. A Windows version (bootstrap only, local disk) runs the generated `.bat` with `cmd /c`, but only on Windows; see "Not yet verified". |
| `tests/test_environment.py`, `tests/test_cli.py` | `uv` as the default engine, `--python`, and config compatibility. |

### Docs

* `docs/environments.md`: a "Provisioning an environment with `uv`" section (choosing Python, automatic and manual installation, `uv.lock`, disk space). `pip` is now described as the older engine. Also fixes `environment create` → `environment new`.
* `docs/administration.md`:
  * the bootstrap needs no Python: how uv is fetched, why Python is copied, which hosts the nodes must reach, the new layout and sizes, and how Python patch versions update;
  * why `module load` remains;
  * a "uv environments" smoke test.
* `docs/known-words.txt`: `lockfile`, `subcommand`, `uv`.

# Rolling it out (admin checklist)

1. **Merge and release.** As the existing rollout note says, the first bootstrap with the new layout must run from a wheel built from the release commit (`hatch build`, then `hipercow dide bootstrap dist/hipercow-<version>-py3-none-any.whl`), before publishing to PyPI.
2. **Run the bootstrap** from a machine that can reach github.com. The first run downloads uv onto the share. Check that each job log shows `Downloading cpython-3.x…`, `Copying python from …` and `… is now current for python 3.x`.
3. **Check the nodes can reach** `releases.astral.sh` (Python), and `pypi.org` and `files.pythonhosted.org` (packages).
4. **Smoke-test both drivers:** `hipercow task create --wait -- echo hello`, then the uv-environment commands in `docs/administration.md` ("uv environments").
5. **On Linux, run `module show Python/3.12`.** If the module sets `PYTHONPATH` or `PYTHONHOME`, those would also reach hipercow's own Python, since `module load` stays in the job scripts. `LD_LIBRARY_PATH` doesn't matter (see below).
6. **Tell users** that new environments use uv, that they can choose a version with `--python`, and that existing environments are unaffected.
7. **Later:** once nobody uses `pip` environments, delete the `module load Python` line from `batch_linux.py`. The cluster's Python modules and Windows Pythons are then unused by hipercow.

# What was verified, and how

Everything was run on a Linux workstation with uv 0.12.21, the version a fresh install gets today.

* **Full test suite: 297 passed, 1 skipped.** The skip is the Windows-only bootstrap test. One test went with the cleanup. `hatch run lint:all` (ruff, black, mypy) is clean across the whole repo. `mkdocs build --strict`, with the spellchecker, passes.
* **The real bootstrap and real job scripts ran end to end** (`tests/zzz/test_bootstrap_dide.py`):
  * uv was downloaded from GitHub and its checksum verified;
  * the job ran with a `PATH` of just `bash`, `cat`, `mktemp` and similar tools, with no Python, and an empty `HOME`;
  * it installed hipercow into a copy of Python 3.13.15 on the fake share and switched `current`, and the temporary directory was deleted;
  * the installation's hipercow then ran a provisioning job that built a Python 3.12 uv environment, and two task jobs (`cowsay`, and `python` reporting 3.12 from the environment's own copy);
  * `HOME` was still empty at the end.
* **The worked example** was re-run with the final code (steps 3–5 and 8), including the side-by-side versions.

### Things testing turned up, and how the design responds

1. **uv on Windows needs a junction for every Python it installs, and junctions can't go on network shares** (from uv's source; see above). Hence the download-then-copy approach, in both the bootstrap and the environment engine.
2. **The copied Python still runs once the original is deleted.** The bootstrap test checks that the installation's `python3` resolves inside the installation.
3. **uv marks its Pythons `EXTERNALLY-MANAGED`**, and `uv pip install` into the copy failed with "This Python installation is managed by uv and should not be modified". The bootstrap removes the marker from the copy. Environments install into a venv, so they aren't affected.
4. **uv accepts the copy as an explicit interpreter**, even with `UV_MANAGED_PYTHON=1`, for both `uv venv --python <copy>` and `UV_PYTHON=<copy>`.
5. **Pinning `UV_PYTHON` to the copy keeps `uv sync` on it.** `uv sync` reuses the venv and downloads nothing. If `requires-python` excludes that version, it fails with "The requested interpreter resolved to Python 3.12.14, which is incompatible with the project's Python requirement" and leaves the venv alone.
6. **`module load Python` can't hijack hipercow's Python through `LD_LIBRARY_PATH`.** The standalone `python3.x` binary doesn't load `libpython.so` (it isn't in `NEEDED`), and it uses `RPATH $ORIGIN/../lib`. `PYTHONPATH`/`PYTHONHOME` would still apply if the module set them (checklist step 5).
7. **`uv run --no-project script.py` runs the script directly** with the downloaded interpreter, so `sys.base_prefix` is the Python to copy. It also sets `UV` for the script, but the path is passed explicitly with `--uv` anyway.
8. **uv's release archives** contain `uv-x86_64-unknown-linux-gnu/uv` (in a `.tar.gz`) and `uv.exe` (in a `.zip`), 18–20 MB each. GitHub publishes a `.sha256` for each, which is checked.
9. **With no version requested, uv picks the latest stable release** (3.14.7), so environments created months apart can differ. The docs recommend `--python` or `.python-version`.
10. **A user's `uv.toml` can't switch to the system Python**: environment variables take priority (verified with `python-preference = "system"`). The bootstrap also sets `UV_NO_CONFIG`.
11. **`uv sync` would normally create `.venv` in the project.** `UV_PROJECT_ENVIRONMENT` prevents it (checked in a slow test).
12. **`uv lock` needs an interpreter** and would download one into the home directory, so the slow test locks with the running Python.
13. **Sizes.** A bootstrap installation is about 200 MB (Python ~110 MB, the uv wheel ~50 MB, other dependencies). An environment with numpy came to about 170 MB. The uv cache is mostly hard links.

# Not yet verified (needs the real cluster or CI)

* **Anything on the DIDE cluster.** The checklist above covers it.
* **Windows, in general.** The `.bat` and the uv environment engine haven't run on Windows. `test_bootstrap_on_windows` will run the real bootstrap `.bat` on `windows-latest` in CI once the branch is pushed, on local disk.
* **Windows, running from the share.** hipercow, `python.exe` and `uv.exe` now run from `\\wpia-hn-app\hipercow` and the project share. Earlier pipx launchers ran from the share without trouble, but micromamba failed there. If uv does too, `HIPERCOW_UV` can point the environment engine elsewhere. The bootstrap's own uv would need copying to the nodes, like micromamba.
* **Copy time onto the share.** Each bootstrap job and each new environment copies about 100 MB of Python (a few thousand files) onto SMB/CIFS. That's a one-off per installation or environment, but worth timing.
* **Startup time.** Python's standard library now loads from the share at every job start.
* **Linux CIFS.** The copy contains a few relative symlinks (`bin/python3 -> python3.13`), the same requirement existing venvs already have. The uv binary needs its exec bit: it's written with mode 755 from the admin's machine, and the smoke test will show if the mount drops it.
* **Network access** from the nodes to `releases.astral.sh`, and from the admin's machine to github.com.
* **`PYTHONPATH`/`PYTHONHOME` from `module load Python`** (checklist step 5).

# Possible follow-ups

* Delete `module load Python` from the Linux job scripts once `pip` environments are retired.
* Add 3.14 to the bootstrap's default versions and to `check_python_version`; uv makes this free.
* Remove old uv versions from `bootstrap-py-<platform>/uv/` once no installation uses them.
* Share one copy of each Python between a project's environments, to save about 110 MB per extra environment.
* Check `--python` on the client, so typos are caught before a cluster job.
* Support scripts with inline dependencies ([PEP 723](https://peps.python.org/pep-0723/)) via `uv run --script`.
* Show each environment's engine and Python version in `hipercow environment list`.
