# Setting up the bootstrap

Currently this is manual, we'll automate it soon.

Run:

```
hatch build
```

to build the package.  Copy the `.whl` file to the bootstrap inputs (`\\wpia-hn\hipercow\bootstrap-py-windows\in`)

Edit or write the batch file, as `\\wpia-hn\hipercow\bootstrap-py-windows\in\bootstrap-311.bat`

```batch
call set_python_311_64
set PIPX_HOME=\\wpia-hn\hipercow\bootstrap-py-windows\python-311\pipx
set PIPX_BIN_DIR=\\wpia-hn\hipercow\bootstrap-py-windows\python-311\bin
python pipx.pyz install --force "in\hipercow-0.0.2-py3-none-any.whl"
```

Go to the [cluster portal](https://mrcdata.dide.ic.ac.uk/hpc)

* **Job name**: anything
* **Working dir**: `\\wpia-hn\hipercow\bootstrap-py-windows\in`
* **Job(s) to run**: `bootstrap-311.bat`

The job will take a little more than a minute if run against an entirely empty destination directory.  It might be somewhat faster a second time around.
