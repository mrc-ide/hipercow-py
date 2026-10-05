# Adding conda support to hipercow-py

Branch: `conda-environments` (not yet committed or pushed)

## Summary

Users can now create conda environments on the cluster (a full worked example follows below):

```shell
hipercow environment new --engine conda
hipercow environment provision conda install -c bioconda samtools
hipercow task create -- samtools view -c data/reads.bam
```

The recommended approach, now implemented, is a new **`Conda` environment engine** that uses **micromamba**:

* micromamba is a single self-contained executable, about 18 MB on Linux and 11 MB on Windows. It needs no installation, no base environment and no `conda init`.
* The cluster admin places **one copy per platform on the existing `\\wpia-hn\hipercow` share**, next to the Python bootstrap. The job scripts point hipercow at it with the environment variable `HIPERCOW_MICROMAMBA`.
* Each environment is a **path-based prefix inside the project's hipercow root**, on the network share, so every node can see it. This follows how the pip engine stores its venv.
* Tasks run through `micromamba run`, which activates the environment properly: it sets `PATH` and `CONDA_PREFIX` and runs the packages' own activation scripts.

Nothing needs to be installed on user machines or on the nodes' local disks. The one admin action is copying two files onto the share (see "Rolling it out" below).

## Worked example: what a user does

This follows a researcher who wants `samtools` and `pysam` for a small bioinformatics project, from an empty project to results.

> **Where the output comes from.** The output shown is real. It was captured on a Linux workstation with hipercow's `example` driver, which runs the same provisioning and task code locally instead of on a cluster node. Three things couldn't be run exactly as written without the cluster:
>
> * the DIDE login and driver setup in step 2;
> * `--wait` (each task was run and its log printed instead);
> * `--cores 4`, because the local driver allows only 1 core, so that job was run with 1 core.
>
> On the cluster you would also see job-submission messages and a progress spinner, but the task output is the same. Lines marked *(cluster)* describe what the DIDE driver prints, taken from the code rather than from a real cluster run.

### 1. The project

The project lives on a network share that the cluster can see, such as a folder on the Q: drive or a project share. That's the same requirement hipercow already has.

```text
reads-project/
├── environment.yml
├── data/
│   ├── example.sam
│   └── example.fastq
└── scripts/
    └── summarise.py
```

`environment.yml` describes the software the tasks need:

```yaml
channels:
  - conda-forge
  - bioconda
dependencies:
  - python=3.12
  - samtools
  - pysam
```

`scripts/summarise.py` is an ordinary Python script that uses `pysam` from the conda environment:

```python
import sys

import pysam

path = sys.argv[1]
with pysam.AlignmentFile(path) as f:
    reads = list(f)
mapped = sum(not r.is_unmapped for r in reads)
print(f"{path}: {len(reads)} reads, {mapped} mapped")
```

### 2. One-off setup

Users do this once per computer (authentication) and once per project (everything else). None of it is new:

```shell
hipercow dide authenticate          # once per computer
cd /path/to/share/reads-project     # or Q:\reads-project on Windows
hipercow init .
hipercow driver configure dide-linux
```

Choose `dide-linux` for conda work. bioconda publishes nothing for Windows, so `samtools` can't be installed there at all.

### 3. Create and provision the environment

```console
$ hipercow environment new --engine conda
i Creating environment 'default' using 'conda'

$ hipercow environment provision
```

With no command given, hipercow finds `environment.yml` and records the command `conda install --file environment.yml`. It then submits a provisioning job to the Linux nodes. On the node, micromamba creates an empty environment in `hipercow/py/env/default/contents/conda-linux/` and installs the packages into it. The installation log shows where each package came from:

```text
  + htslib                    1.24  ha79157c_0            bioconda          1MB
  + pysam                   0.24.1  py312hf5ad864_0       bioconda          2MB
  + python                 3.12.14  h5f976f7_3_cpython    conda-forge      23MB
  + samtools                  1.24  h9dcdb79_1            bioconda        504kB
...
Transaction finished
```

*(cluster)* The log streams to the user's terminal while the job runs, and ends with `✔ Provisioning completed in <n>s`. The first provisioning took about a minute in testing. It will depend on the size of the environment and the speed of the share.

### 4. Run jobs

Any command can be run as a job, and it sees everything in the environment. Put `--` before the command so that hipercow doesn't treat the command's own options (such as `-c`) as hipercow options.

```console
$ hipercow task create --wait -- samtools flagstat data/example.sam
eb50c5495aa7d259b6db65a3d4f317b4
3 + 0 in total (QC-passed reads + QC-failed reads)
3 + 0 primary
0 + 0 secondary
...
2 + 0 mapped (66.67% : N/A)
2 + 0 primary mapped (66.67% : N/A)
...
```

*(cluster)* With `--wait`, hipercow prints the task id, waits for the job, and streams its output as it runs. Without `--wait` it prints the task id and returns straight away, and you check on the job later:

```console
$ hipercow task create -- python scripts/summarise.py data/example.sam
86db67c0ed8c4d9459803eda4c396b5e

$ hipercow task status 86db67c0ed8c4d9459803eda4c396b5e
success

$ hipercow task log 86db67c0ed8c4d9459803eda4c396b5e
data/example.sam: 3 reads, 2 mapped
```

Multi-core jobs work as they already do. Request cores with `--cores` and tell the program to use them. The cluster puts the number of allocated cores in `HIPERCOW_CORES`, and this passes through into the conda environment (verified).

```shell
hipercow task create --cores 4 -- samtools sort -@ 4 -o data/example.sorted.bam data/example.sam
```

### 5. Add software later

Install extra tools at any time. Anything already in the environment stays:

```shell
hipercow environment provision conda install -c bioconda bcftools
```

Alternatively, add the package to `environment.yml` and run `hipercow environment provision` again. In testing, adding `seqkit` to the file and re-provisioning installed only `seqkit`, and every earlier package (including `bcftools`) was kept:

```text
  + seqkit   2.13.0  he881be0_0  bioconda      7MB
```

A job afterwards confirmed that all the tools were there:

```text
samtools 1.24
bcftools 1.24
seqkit v2.13.0
pysam 0.24.1
```

Python packages from PyPI go in with `pip`, once `python` is in the environment (as it is here):

```shell
hipercow environment provision pip install tqdm
```

### 6. A second environment (optional)

A separate environment is useful for tools that conflict, or to try a new version without disturbing queued jobs:

```console
$ hipercow environment new --name qc --engine conda
i Creating environment 'qc' using 'conda'

$ hipercow environment provision --name qc conda install -c bioconda seqkit

$ hipercow environment list
default
empty
qc

$ hipercow task create --environment qc -- seqkit stats data/example.fastq
811b145069849c7ac2004ad43ec29412

$ hipercow task log 811b145069849c7ac2004ad43ec29412
file                format  type  num_seqs  sum_len  min_len  avg_len  max_len
data/example.fastq  FASTQ   DNA          3       32       10     10.7       12
```

Jobs without `--environment` use `default`.

### 7. When things go wrong

**A typo in a package name.** Provisioning fails:

```console
$ hipercow environment provision conda install -c bioconda samtoolz
Error: Provisioning failed
```

The provisioning log, at `hipercow/py/env/default/provision/<id>/log`, says why:

```text
error    libmamba Could not solve for environment specs
    The following package could not be installed
    └─ samtoolz =* * does not exist (perhaps a typo or a missing channel).
```

*(cluster)* On the cluster this log streams to the terminal while the job runs, so users see the reason straight away. hipercow then prints `✖ Provisioning failed after <n>s!` and the location of the log. A failed install leaves the existing environment unchanged. The environment's install history (`conda-meta/history`) had no entry for the failed attempt.

**A program that isn't in the environment.** The task is marked `failure`, and the log explains why:

```console
$ hipercow task log <id>
/tmp/mambaf...: line 5: exec: seqkit: not found
```

In testing this happened when running `seqkit` without `--environment qc`, because `seqkit` was only installed in `qc` at that point.

**Forgetting the `--`.** hipercow tries to read the program's options as its own:

```console
$ hipercow task create samtools view -c data/example.sam
Error: No such option '-c'.
```

**A mistyped environment name.** This is caught when the job is created:

```console
$ hipercow task create --environment nope -- ls
Error: No such environment 'nope'
```

A task's status comes from the program's exit code. Some tools exit with 0 even after printing an error. For example, `seqkit stats` run on a SAM file exits 0, so hipercow reports `success`. If results look wrong, read `hipercow task log`.

### 8. Housekeeping

```console
$ hipercow environment provision conda clean --all    # empty the package cache (can halve disk use)
$ hipercow environment delete --name qc               # remove an environment you no longer need
i Attempting to delete environment 'qc'; ...
✔ Done!
```

## Why micromamba, and not the alternatives

| Option | Verdict |
| --- | --- |
| **micromamba binary on the hipercow share** (chosen) | One file per platform, the same code path on Windows and Linux, and it reuses the share and path conventions hipercow already relies on. Its CLI accepts the same `install`/`remove`/`-c` commands users already know from conda. Version 2 defaults to conda-forge and never touches Anaconda's `defaults` channel. |
| Full Miniforge/Anaconda installed on the share | A large install with a shared base environment on a network drive. It needs `conda init`/activation shell plumbing and is slower. Anaconda's `defaults` channel also comes with commercial licence terms. |
| `module load Miniforge` on the Linux nodes | Linux only, and ties hipercow to the node image. It doesn't help the Windows cluster. |
| pixi / conda-lock / containers | Good tools, but bigger changes to the user workflow. They could be added later as further engines. |

## How it works

```text
your machine                              cluster node (Linux or Windows)
------------                              -------------------------------
hipercow environment provision ...  --->  provision run.sh / run.bat
  Conda.check_args() validates cmd          sets HIPERCOW_MICROMAMBA
  writes provision/<id>/data                hipercow environment provision-run
  submits the job                             Conda.create()     (first time only)
                                                micromamba create --yes --prefix <env>
                                              Conda.provision()
                                                micromamba install --yes --prefix <env> ...

hipercow task create ...  ------------->  task_run.sh / task_run.bat
                                            hipercow task eval
                                              Conda.run()
                                                micromamba run --prefix <env> <cmd>
```

Checking arguments happens on the client and doesn't need micromamba. Translating them to micromamba commands happens on the node, where the prefix path (`Q:\...` or `/mnt/homes/...`) and the platform are known.

### Layout within the project

```text
<project>/hipercow/py/env/<name>/
  config                   {"engine": "conda"}
  provision/<id>/          data, log, result, run.sh or run.bat (as for pip)
  contents/
    conda-linux/           the environment itself (the "prefix")
    mamba-linux/           micromamba "root prefix" for this environment
      .mambarc             channels: [conda-forge]
      pkgs/                package cache (can be emptied with `conda clean --all`)
    conda-windows/         only if provisioned from Windows nodes
    mamba-windows/
```

Everything lives under `env/<name>/`, so `hipercow environment delete` removes it all. Each platform gets its own directory because conda packages are platform-specific.

### Environment variables set by the engine

| Variable | Value | Why |
| --- | --- | --- |
| `MAMBA_ROOT_PREFIX` | `contents/mamba-<platform>` | Keeps micromamba's cache and state inside the project, not in a home directory on the node. |
| `MAMBARC` and `CONDARC` | `contents/mamba-<platform>/.mambarc` | micromamba then reads **only** this file. Both are needed because micromamba reads both if they are set (verified). |

## Changes, file by file

### New: `src/hipercow/environment_engines/conda.py`

The `Conda(EnvironmentEngine)` class implements the same interface as `Pip`:

* `path()` returns `contents/conda-<platform>`, and the new `path_root_prefix()` returns `contents/mamba-<platform>`.
* `create()` writes a `.mambarc` containing `channels: [conda-forge]`, unless one already exists, then runs `micromamba create --yes --prefix <path>` to make an empty environment.
* `check_args(cmd)`, which runs on the client:
  * No command: uses `environment.yml` or `environment.yaml` if present, giving `conda install --file environment.yml`. Otherwise it errors, as pip does.
  * The first word must be `conda`, `mamba` or `micromamba` (all equivalent), or `pip`.
  * The subcommand must be `install`, `update`, `remove`, `uninstall` or `clean`. `create` is refused because hipercow creates the environment.
  * `-n`/`--name`, `-p`/`--prefix` and `-r`/`--root-prefix` are refused, including the `--prefix=...` form, because hipercow owns the location.
* `provision(cmd)`, which runs on the node:
  * conda commands become `micromamba <subcommand> --yes --prefix <path> <args...>`.
  * `clean` has no `--prefix`, because micromamba rejects it (verified), and it acts on the cache.
  * `pip ...` becomes `micromamba run --prefix <path> pip ...`, installing into the conda environment.
* `run(cmd)` becomes `micromamba run --prefix <path> <cmd>`. Environment variables, the working directory, the log file and exit codes pass through.
* `_micromamba()` looks up the executable: `$HIPERCOW_MICROMAMBA` first (with a clear error if it points at a missing file), then `micromamba` on `PATH`, otherwise it errors with guidance.

### `src/hipercow/environment_engines/__init__.py`

Exports `Conda`.

### `src/hipercow/environment.py`

* `environment_new()` accepts `engine="conda"`. The error message and docstring are updated.
* `environment_engine()` returns `Conda(root, name)` for `engine == "conda"`.

### `src/hipercow/cli.py`

The `--engine` help text now names `pip` and `conda`. No behaviour change: `environment provision` already passes unknown options like `-c bioconda` through, and a new test confirms it.

### `src/hipercow/dide/batch_linux.py` and `batch_windows.py`

Both the task and the provisioning templates now set the location of micromamba:

```text
export HIPERCOW_MICROMAMBA=/mnt/cluster/Hipercow/bootstrap-py-linux/micromamba/micromamba   # Linux
set HIPERCOW_MICROMAMBA=I:\bootstrap-py-windows\micromamba\micromamba.bat                   # Windows
```

`I:` is already mapped to `\\wpia-hn-app\hipercow` by these scripts, and `/mnt/cluster/Hipercow` is the same share seen from Linux. The line is harmless for pip and empty environments.

### `.github/workflows/test.yml`

Adds `mamba-org/setup-micromamba@v3` (installing only the binary, pinned to `2.9.0-0`), so the real end-to-end conda test runs in CI on **Ubuntu, macOS and Windows**.

### Tests

| File | What |
| --- | --- |
| `tests/test_environment_conda.py` (new) | 13 unit tests with mocked `subprocess.run`: paths per platform, creation (including the `.mambarc` and not overwriting an existing one), the exact micromamba command lines for install, remove, clean, pip and run, the automatic `environment.yml`/`.yaml` default, argument validation (commands, subcommands, forbidden flags) and executable lookup (env var, missing file, `PATH`, not found). |
| `tests/zzz/test_environment_conda.py` (new, `slow`) | Real end-to-end run: the `example` driver, `environment.yml` with `ripgrep`, automatic provisioning, a task running `rg --version` that succeeds, and a failing task that is reported as `FAILURE`. It also points `CONDARC` at a user config with an unreachable channel to prove user configuration doesn't leak in. It is skipped when micromamba isn't available. |
| `tests/test_environment.py` | The test that expected `conda` to be rejected now uses an unknown engine. A new test creates a conda environment. |
| `tests/test_cli.py` | `environment new --engine conda`, and `-c bioconda` passing through `environment provision`. |
| `tests/dide/test_batch_*.py` | Check that all four generated scripts set `HIPERCOW_MICROMAMBA`. |

### Docs

* `docs/environments.md`: a new user section, "Provisioning an environment with `conda`", covering automatic and manual installation, pip inside conda, channels, Linux vs Windows, running tasks (and why `--` matters), and disk space.
* `docs/administration.md`: a new "Installing micromamba" section with download, placement and verification steps.
* `docs/roadmap.md`: conda removed from "missing features".
* `docs/known-words.txt`: adds `bioconda` and `micromamba` for the spellchecker.

## Rolling it out (admin checklist)

1. **Merge and release** hipercow-py as usual, then run `hipercow dide bootstrap` so the nodes get the new version. The updated batch templates come from the client, so users also need the new version locally.
2. **Put micromamba on the share.** With `\\wpia-hn\hipercow` mounted:

   ```shell
   VERSION=2.9.0-0
   URL=https://github.com/mamba-org/micromamba-releases/releases/download/$VERSION
   mkdir -p <share>/bootstrap-py-linux/micromamba <share>/bootstrap-py-windows/micromamba
   curl -L -o <share>/bootstrap-py-linux/micromamba/micromamba       $URL/micromamba-linux-64
   chmod +x <share>/bootstrap-py-linux/micromamba/micromamba
   ```

3. **Smoke-test both platforms** with a `hipercow task create --wait -- <path-to-micromamba> --version` job on each driver. If Linux gives "Permission denied", run `chmod +x` from a Linux node, because CIFS mount options may drop the exec bit.
4. **Full test on Linux**: create an environment, provision `conda install -c bioconda samtools`, and run `samtools --version` as a task. This also confirms the nodes can reach `conda.anaconda.org`, which is a different host from PyPI and may need allowing through the firewall.
5. **Tell users** to prefer `dide-linux` for conda work: bioconda has no Windows builds.

## What was verified, and how

Everything below was run on a Linux workstation against the **official micromamba 2.9.0 release binary**, the exact artefact the admin would deploy.

* **Full test suite: 251 passed**, including both slow end-to-end tests (pip and conda). The run was repeated once with micromamba found through `HIPERCOW_MICROMAMBA` (as on the cluster) and once through `PATH` (as in CI). Lint (ruff, black, mypy) is clean, and `mkdocs build --strict` (with the spellchecker) passes.
* **The worked example above** was run end to end: automatic provisioning from `environment.yml`, `samtools` and `pysam` jobs, adding tools both with a command and by editing `environment.yml`, a second environment, deleting an environment, and each of the error cases shown.
* **Manual CLI walkthrough**, run exactly as a user would with the `example` driver: `environment new --engine conda`, then `provision conda install -c bioconda samtools`, `provision conda install python=3.12 pip` and `provision pip install cowsay`. Tasks running `samtools --version` and a Python/cowsay script both succeeded. A task running `samtools view` on a missing file was reported as a failure.
* **The regression test was checked to fail without the fix.** With the `MAMBARC`/`CONDARC` override removed, the end-to-end test fails at provisioning, and with it restored the test passes.

### Things testing turned up, and how the design responds

1. **Channels on the command line replace micromamba's built-in default.** With no config file, `-c bioconda samtools` fails to solve because conda-forge disappears. **Fix:** `create()` writes a `.mambarc` listing conda-forge, after which `-c bioconda` *adds* to conda-forge (samtools 1.24 solves).
2. **The user's `~/.condarc` leaked in.** On the test machine it contained `defaults`. The result was python from Anaconda's `pkgs/main`, samtools resolving to 1.9 and then being *downgraded* to 1.3.1. **Fix:** point both `MAMBARC` and `CONDARC` at hipercow's file. micromamba reads both variables when both are set, so both must be overridden, including in CI where setup-micromamba sets `CONDARC`. After the fix: samtools 1.24, python from conda-forge, no `pkgs/main`.
3. **micromamba ignores config files without a conventional name** such as `.condarc`, `.mambarc` or `*.yml`. The first version of the regression test used `user.condarc` and passed vacuously. It was rewritten to use a real `.condarc`, and now fails without the fix.
4. **If hardlinks fail** (simulated with the cache and the environment on different filesystems), micromamba quietly copies instead. So a share that can't do hardlinks still works, at up to about double the disk use.
5. **`micromamba clean` rejects `--prefix`**, so the engine special-cases it. `clean --all` took the cache from 227 MB to 52 KB, and the environment and later installs still worked.
6. **Exit codes, environment variables and the working directory pass through `micromamba run`.** Exit 3 stays 3, and a missing program gives 127, which hipercow reports as a task failure.
7. **`environment.yml` with a `pip:` section** installs correctly with `install --file`, and `name:` in the file is ignored in favour of `--prefix`.
8. **`jq` has no Windows build on conda-forge**, so the integration test uses `ripgrep`, which is available for linux-64, win-64, osx-64 and osx-arm64 (checked).
9. **bioconda has no Windows builds** (`samtools` can't be solved for win-64), which is why the docs steer conda users to `dide-linux`.
10. **`hipercow task create samtools --version` fails** unless a `--` comes before the command, because click treats `--version` as a hipercow option. This is existing behaviour, now documented in the conda section.

## Not yet verified (needs the real cluster or CI)

* **Windows nodes.** The Windows code path is identical apart from the paths, and CI will run the real end-to-end test on `windows-latest` once the branch is pushed. It has not been run on DIDE Windows nodes.
* **The DIDE shares themselves.** Symlinks inside conda packages on the Linux CIFS mounts are the same requirement pip venvs already have on Linux, so they're expected to work. File locking and the exec bit on the micromamba binary still need the smoke test in the checklist.
* **Outbound access from the nodes to `conda.anaconda.org`**, and to `repo.prefix.dev` if anyone adds that channel.
* **Windows path length.** An environment deep inside a project on a mapped drive can exceed Windows' 260-character limit for some packages. The pip engine has the same exposure. Enabling `LongPathsEnabled` on the Windows nodes would remove the risk.

## Possible follow-ups

* A `hipercow dide bootstrap-micromamba` admin command to download, place and verify the binaries, like `hipercow dide bootstrap` does for Python.
* A package cache shared by all of a user's environments (via `CONDA_PKGS_DIRS`) to cut download time and disk use. The cost is that `environment delete` would no longer clean everything up.
* Support for lock files (`conda-lock.yml` / `micromamba create --file lockfile`) for exactly reproducible environments.

## Existing issues noticed along the way (not changed)

* `docs/environments.md` says `hipercow environment create --name dev`, but the command is `environment new`.
* The slow tests in `tests/zzz/` fail when run on their own ("No such driver 'example'"), because the example driver is only registered once other test modules have imported it. They pass in a full run, which is how CI runs them.
