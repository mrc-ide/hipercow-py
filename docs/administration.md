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
