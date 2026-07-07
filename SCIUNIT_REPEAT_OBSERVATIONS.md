# Sciunit Repeat Observations

## Observed Behavior

The FLINC repeat kernel invokes Sciunit as:

```text
sciunit given <connection_file> repeat latest ...
```

Sciunit checks out the selected execution into a shared project working directory:

```text
~/sciunit/<project>/cde-package
```

and rewrites `cde.log` when repeat is invoked with replacement arguments.

## Operational Issue

Only one repeat/check-out flow should run against the same Sciunit project at a time. Running `sciunit checkout`, starting another repeat kernel, or reimporting/reopening the same project while a repeat kernel is alive can replace `cde-package` underneath the running process. The live kernel may then show a deleted current working directory in `/proc`, and notebook-local imports can fail even when the checked-out package contains the files.

## Key Cache Note

`sciunit unlock <execution id> --key <shared-key>` caches the key locally but does not validate it at unlock time. An incorrect key is only detected later during repeat when Sciunit attempts to restore protected files.

## Suggested Sciunit Follow-Ups

These are not required for the FLINC import-path fix, but would make repeat more robust:

- Validate unlock keys when `sciunit unlock` is run, if the package is locally available.
- Avoid mutating a shared `cde-package` directory for live repeat kernels, or use per-repeat checkout directories.
- Consider rejecting concurrent repeat/check-out operations against the same project unless explicitly requested.
