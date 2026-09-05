# FLINC-NASA-DEMO_SEP_26

This branch starts from the local `nasa-demo` branch at `f89bd96` and adds
FLINC audit handling for container-specific environment variables. Its purpose
is to let a captured notebook use the current AWS container's credentials when
starting distributed Dask workers through ECS/Fargate.

## Problem

The IMERG Dask notebook failed in `FargateCluster(...)` with
`CredentialRetrievalError` and HTTP 400, `CredentialsV2Request: Credentials not found`.
The captured `AWS_CONTAINER_CREDENTIALS_RELATIVE_URI` referred to an earlier
container's credentials endpoint. The live container had a working endpoint.

Deleting the variable from `cde.full-environment.cde-root` alone was
insufficient. Sciunit's `CheckoutContext` deletes and restores the package on
every repeat startup, bringing back the captured value. Editing the file also
does not change an already-running kernel's environment.

CDE already has the right mechanism for this case:
`ignore_environment_var=<name>` in `cde.options`. During repeat, CDE saves the
live launcher value for ignored variables before it clears the process
environment and reloads `cde.full-environment`. When the ignored variable is
encountered in the captured environment file, CDE skips the captured value and
restores the live launcher value.

## Changes

- `handler.py` routes `sciunit exec` through `audit-sciunit.py`, located beside
  the handler, and propagates the child process's exit code.
- `audit-sciunit.py` wraps `sciunit2.core.capture` in the launcher process, so
  the selected `ignore_environment_var` entries are added after CDE creates the
  package and before Sciunit commits it.
- The selected variables remain in `cde.full-environment.cde-root`. This is
  intentional: CDE uses those captured entries as the point where it substitutes
  the current launcher value during repeat.
- Repeat startup remains the standard FLINC/Sciunit path. No repeat-time
  bootstrap or environment-file cleanup is needed for packages audited with this
  branch.

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
from the host. Sciunit source code is unchanged; FLINC adjusts the audit launch
path before Sciunit commits the package.

## Using the branch

Use the existing installation instructions in `README.md`. Keep
`audit-sciunit.py` beside `handler.py`. For a new installation, the installer
uses `handler.py` for the audit kernel and the audit wrapper is applied
automatically.

This branch fixes newly audited executions. Existing Sciunit executions that
were captured before these `cde.options` entries were added should be audited
again if they need live AWS/ECS launcher values during repeat.

Linux `/proc` must be readable from replay, and the launching container must
already have valid AWS credentials and the required ECS permissions/networking.
The fix does not create credentials or grant permissions. If a selected variable
is absent from the launcher, it remains absent in the kernel.

Generated local `audit-kernel/`, unpacked `sciunit/`, and the installed path
added to `repeat-kernel/kernel.json` are not part of this branch. The existing
installer generates the kernel paths; committing a generated handler entry would
cause it to be inserted twice on a fresh installation.

## Validation

The CDE behavior was checked with a dummy environment variable:

- With `ignore_environment_var` present and the variable still present in
  `cde.full-environment`, repeat saw the live launcher value.
- After removing the variable from `cde.full-environment`, repeat saw the
  variable as missing.

During the live IMERG investigation, the current container's credentials were
validated separately with an authenticated ECS `describe_clusters` call returning
HTTP 200 and `ACTIVE`. That validates credentials; it is not a full distributed
IMERG workflow test. Existing interrupt-handler errors and the captured
environment's missing `stack_data` dependency are outside this change.
