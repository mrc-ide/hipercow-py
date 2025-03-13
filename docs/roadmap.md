# Roadmap

## For users of the R `hipercow`

This package will feel quite different to the R version of `hipercow`; our aim here is to provide a somewhat [Pythonic](https://blog.startifact.com/posts/what-is-pythonic/) interface to the cluster that takes the best *ideas* from the R version without directly implementing the same API.  The two packages currently share the same name but do not yet interact directly -- this may change in future as they develop,

The most obvious difference at the moment is that all interaction with the python version occurs via the command line interface.  We have started here because it seems far less common to use the [REPL](https://en.wikipedia.org/wiki/Read%E2%80%93eval%E2%80%93print_loop) from Python than it does in R.  This change has many positives; it makes running arbitrary programs (e.g., python packages with commandline interfaces, bioinformatics tools, etc) very straightforward, so long as they can be found.

## Missing features

Many of these are features that will feel familiar to users of the R version.

* The concept of "resources" for a task (e.g., the number of cores etc).  This will likely be added soon.
* Running functions, or expressions of python code, without writing it out as a file.  This requires thoughts and opinions about interface and we welcome feedback and ideas.
* Running many related tasks at once and interacting with this bundle.  We do not know what the easiest interface for this looks like and welcome ideas and feedback.
* The ["worker" patterns](https://mrc-ide.github.io/hipercow/articles/workers.html) for a faster, less persistent, queue.
* Review the effect of a series of attempts to install packages
* Retry failed tasks
* Support multiple mounted windows shares at once
* Run on our new Linux cluster
* Retrieve information about the cluster that you are running on
* Support for setting up [conda environments](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html), particularly to support bioinformatics workflows.

There are also many rough edges:

* The way that progress and messages are printed out is spartan at best, and a far cry from our standard use of the [`cli` R package](https://github.com/r-lib/cli)
* If an error is thrown, you will see a gory stacktrace
* The provisioning is pretty basic
* Not all error output makes it from the cluster back to your screen
