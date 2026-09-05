# FLINC-NASA-DEMO_SEP_26

This branch starts from the local `nasa-demo` branch at `f89bd96` and adds
FLINC replay startup handling for container-specific environment variables.
Its purpose is to let a captured notebook use the current AWS container's
credentials when starting distributed Dask workers through ECS/Fargate.

## Problem

The IMERG Dask notebook failed in `FargateCluster(...)` with
`CredentialRetrievalError` and HTTP 400, `CredentialsV2Request: Credentials not found`.
The captured `AWS_CONTAINER_CREDENTIALS_RELATIVE_URI` referred to an earlier
container's credentials endpoint. The live container had a working endpoint.

Deleting the variable from `cde.full-environment.cde-root` alone was insufficient:
Sciunit's `CheckoutContext` deletes and restores the package on every repeat
startup, bringing back the captured value. Editing the file also does not change
an already-running kernel's environment.

## Changes

- `repeat-handler.py` routes Sciunit through `repeat-sciunit.py`, located beside
  the handler, and propagates the child process's exit code.
- `repeat-sciunit.py` wraps `sciunit2.core.repeat` in the launcher process, so its
  preparation runs after package restoration and before CDE starts Python.
- Preparation removes the selected variables from `cde.full-environment*`,
  preserving the NUL-delimited format and other entries. It adds corresponding
  `ignore_environment_var` entries to `cde.options` without duplicating them.
- For `-m ipykernel_launcher`, startup uses a Python bootstrap that reads the
  still-running launcher's `/proc/<pid>/environ`. It copies only the selected
  variables into the replay Python environment, removes selected keys absent
  from the launcher, and then runs `ipykernel_launcher` with the original arguments.

The bootstrap is needed because the tested CDE build did not retain live
variables once their entries were removed from the captured environment file.
The generated bootstrap contains variable names and a launcher PID, not live
credential values. This fix does not write those values into the package.

## Variables taken from the current launcher

```text
AWS_CONTAINER_CREDENTIALS_RELATIVE_URI
AWS_CONTAINER_CREDENTIALS_FULL_URI
AWS_CONTAINER_AUTHORIZATION_TOKEN
AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE
ECS_AGENT_URI
ECS_CONTAINER_METADATA_URI
ECS_CONTAINER_METADATA_URI_V4
JUPYTER_TOKEN
SESSION_ID
SESSION_OWNER_ID
SESSION_MODE
SCIUNIT_MODE
HOSTNAME
JPY_SESSION_NAME
JPY_PARENT_PID
```

These are runtime inputs for the current container/session. Captured Python,
libraries, datasets, and computation continue to use normal CDE replay behavior,
including its existing filesystem exclusions. This is not complete isolation
from the host. Sciunit source code and capture logic are unchanged.

## Using the branch

Use the existing installation instructions in `README.md`. Keep the new wrapper
beside `repeat-handler.py`. For an existing installation pointing to this checkout,
restart the repeat kernel after updating the files; do not rerun `install.sh`.
The installed repeat kernelspec must invoke `repeat-handler.py` before `sciunit`.
The installer supplies that path for a new installation.

Linux `/proc` must be readable from replay, and the launching container must
already have valid AWS credentials and the required ECS permissions/networking.
The fix does not create credentials or grant permissions. If a selected variable
is absent from the launcher, it remains absent in the kernel.

Generated local `audit-kernel/`, unpacked `sciunit/`, and the installed path added
to `repeat-kernel/kernel.json` are not part of this commit. The existing installer
generates the kernel paths; committing a generated handler entry would cause it
to be inserted twice on a fresh installation.

## Validation

During the live IMERG investigation, after restart:

- The captured credentials URI was absent from the restored full env file.
- The replay kernel used the current container's URI.
- `aiobotocore` selected the `container-role` credentials provider.
- An authenticated ECS `describe_clusters` call returned HTTP 200 and `ACTIVE`.

Local checks also cover preserving unrelated environment entries, repeatable
options updates, and applying cleanup again after a simulated package restore.
The successful ECS request validates credentials; it is not a full distributed
IMERG workflow test. Existing interrupt-handler errors and the captured
environment's missing `stack_data` dependency are outside this change.
