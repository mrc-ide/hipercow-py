# Commandline interface

The primary way we expect people to interact with `hipercow` is via the commandline interface.  This page contains the automatically generated reference documentation for this interface; longer explanations are available elsewhere in the documentation.

::: mkdocs-click
    :module: hipercow.cli
    :command: cli
    :depth: 1
    :prog_name: hipercow
    :list_subcommands: True
    :style: table


## Error handling

If `hipercow` throws an error, by default only the actual error message is thrown and not the whole stacktrace.  Over time, we will try and make these error messages rich enough that you can debug things comfortably with what is shown on screen.

```console
$ hipercow environment new --engine other
Error: Only the 'pip' and 'empty' engines are supported
For more information, run with 'HIPERCOW_TRACEBACK=1'
```

To get more information you can set the `HIPERCOW_TRACEBACK` environment variable, either globally (not recommended except for developing `hipercow`) or locally:

```console
$ HIPERCOW_TRACEBACK=1 hipercow environment new --engine other
Error: Only the 'pip' and 'empty' engines are supported
╭─────────────────────────────── Traceback (most recent call last) ────────────────────────────────╮
│ /home/rfitzjoh/Documents/src/hipercow-py/src/hipercow/cli.py:54 in cli_safe                      │
│                                                                                                  │
│    51 # handling.                                                                                │
│    52 def cli_safe():                                                                            │
│    53 │   try:                                                                                   │
│ ❱  54 │   │   cli()                                                                              │
│    55 │   except Exception as e:                                                                 │
│    56 │   │   _handle_error(e)                                                                   │
│    57                                                                                            │
│                                                                                                  │
│ ╭───────────────────────────── locals ──────────────────────────────╮                            │
│ │ e = Exception("Only the 'pip' and 'empty' engines are supported") │                            │
│ ╰───────────────────────────────────────────────────────────────────╯                            │
│                                                                                                  │
│ /home/rfitzjoh/.local/share/hatch/env/virtual/hipercow/qoF7lZeb/hipercow/lib/python3.13/site-pac │
│ kages/click/core.py:1161 in __call__                                                             │
│                                                                                                  │
│ /home/rfitzjoh/.local/share/hatch/env/virtual/hipercow/qoF7lZeb/hipercow/lib/python3.13/site-pac │
│ kages/click/core.py:1082 in main                                                                 │
│                                                                                                  │
│ /home/rfitzjoh/.local/share/hatch/env/virtual/hipercow/qoF7lZeb/hipercow/lib/python3.13/site-pac │
│ kages/click/core.py:1697 in invoke                                                               │
│                                                                                                  │
│ /home/rfitzjoh/.local/share/hatch/env/virtual/hipercow/qoF7lZeb/hipercow/lib/python3.13/site-pac │
│ kages/click/core.py:1697 in invoke                                                               │
│                                                                                                  │
│ /home/rfitzjoh/.local/share/hatch/env/virtual/hipercow/qoF7lZeb/hipercow/lib/python3.13/site-pac │
│ kages/click/core.py:1443 in invoke                                                               │
│                                                                                                  │
│ /home/rfitzjoh/.local/share/hatch/env/virtual/hipercow/qoF7lZeb/hipercow/lib/python3.13/site-pac │
│ kages/click/core.py:788 in invoke                                                                │
│                                                                                                  │
│ /home/rfitzjoh/Documents/src/hipercow-py/src/hipercow/cli.py:409 in cli_environment_new          │
│                                                                                                  │
│   406 │                                                                                          │
│   407 │   """                                                                                    │
│   408 │   r = root.open_root()                                                                   │
│ ❱ 409 │   environment_new(r, name, engine)                                                       │
│   410                                                                                            │
│   411                                                                                            │
│   412 @environment.command(                                                                      │
│                                                                                                  │
│ ╭──────────────────────── locals ────────────────────────╮                                       │
│ │ engine = 'other'                                       │                                       │
│ │   name = 'default'                                     │                                       │
│ │      r = <hipercow.root.Root object at 0x7ff0d8893770> │                                       │
│ ╰────────────────────────────────────────────────────────╯                                       │
│                                                                                                  │
│ /home/rfitzjoh/Documents/src/hipercow-py/src/hipercow/environment.py:45 in environment_new       │
│                                                                                                  │
│    42 │                                                                                          │
│    43 │   if engine not in {"pip", "empty"}:                                                     │
│    44 │   │   msg = "Only the 'pip' and 'empty' engines are supported"                           │
│ ❱  45 │   │   raise Exception(msg)                                                               │
│    46 │                                                                                          │
│    47 │   print(f"Creating environment '{name}' using '{engine}'")                               │
│    48 │   EnvironmentConfiguration(engine).write(root, name)                                     │
│                                                                                                  │
│ ╭────────────────────────────────────────── locals ──────────────────────────────────────────╮   │
│ │ engine = 'other'                                                                           │   │
│ │    msg = "Only the 'pip' and 'empty' engines are supported"                                │   │
│ │   name = 'default'                                                                         │   │
│ │   path = PosixPath('/home/rfitzjoh/Documents/src/hipercow-py/tmp/hipercow/py/env/default') │   │
│ │   root = <hipercow.root.Root object at 0x7ff0d8893770>                                     │   │
│ ╰────────────────────────────────────────────────────────────────────────────────────────────╯   │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
Exception: Only the 'pip' and 'empty' engines are supported
```


This uses [`rich`'s `print_exception`](https://rich.readthedocs.io/en/stable/traceback.html) functionality to print somewhat human readable stack-traces and information on local variables.

Alternatively you can show the raw Python stack trace with `HIPERCOW_RAW_ERROR`:

```console
$ HIPERCOW_RAW_ERROR=1 hipercow environment new --engine other
Traceback (most recent call last):
  File "/home/rfitzjoh/.local/share/hatch/env/virtual/hipercow/qoF7lZeb/hipercow/bin/hipercow", line 8, in <module>
    sys.exit(cli_safe())
             ~~~~~~~~^^
  File "/home/rfitzjoh/Documents/src/hipercow-py/src/hipercow/cli.py", line 56, in cli_safe
    _handle_error(e)
    ~~~~~~~~~~~~~^^^
  File "/home/rfitzjoh/Documents/src/hipercow-py/src/hipercow/cli.py", line 61, in _handle_error
    raise e
  File "/home/rfitzjoh/Documents/src/hipercow-py/src/hipercow/cli.py", line 54, in cli_safe
    cli()
    ~~~^^
  File "/home/rfitzjoh/.local/share/hatch/env/virtual/hipercow/qoF7lZeb/hipercow/lib/python3.13/site-packages/click/core.py", line 1161, in __call__
    return self.main(*args, **kwargs)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^
  File "/home/rfitzjoh/.local/share/hatch/env/virtual/hipercow/qoF7lZeb/hipercow/lib/python3.13/site-packages/click/core.py", line 1082, in main
    rv = self.invoke(ctx)
  File "/home/rfitzjoh/.local/share/hatch/env/virtual/hipercow/qoF7lZeb/hipercow/lib/python3.13/site-packages/click/core.py", line 1697, in invoke
    return _process_result(sub_ctx.command.invoke(sub_ctx))
                           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "/home/rfitzjoh/.local/share/hatch/env/virtual/hipercow/qoF7lZeb/hipercow/lib/python3.13/site-packages/click/core.py", line 1697, in invoke
    return _process_result(sub_ctx.command.invoke(sub_ctx))
                           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "/home/rfitzjoh/.local/share/hatch/env/virtual/hipercow/qoF7lZeb/hipercow/lib/python3.13/site-packages/click/core.py", line 1443, in invoke
    return ctx.invoke(self.callback, **ctx.params)
           ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/rfitzjoh/.local/share/hatch/env/virtual/hipercow/qoF7lZeb/hipercow/lib/python3.13/site-packages/click/core.py", line 788, in invoke
    return __callback(*args, **kwargs)
  File "/home/rfitzjoh/Documents/src/hipercow-py/src/hipercow/cli.py", line 409, in cli_environment_new
    environment_new(r, name, engine)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
  File "/home/rfitzjoh/Documents/src/hipercow-py/src/hipercow/environment.py", line 45, in environment_new
    raise Exception(msg)
Exception: Only the 'pip' and 'empty' engines are supported
```

We may ask you to do one of these if reporting an issue.
