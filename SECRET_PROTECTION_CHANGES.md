# FLINC Secret Protection Changes

This repository now relies on Sciunit package protection for portable secrets and sensitive PII.

## High-level behavior

- Sciunit protects the generated `cde-package` before it is committed.
- Portable secrets and PII in captured text files are replaced with placeholders.
- The original values are stored in an encrypted vault.
- Broad leakage artifacts such as `history.sqlite` and `cde.full-environment.cde-root`
  are removed from plaintext package storage and preserved only in encrypted form.
- Repeat users must run `sciunit unlock <execution id> --key <shared-key>` before
  replaying a protected execution.

## User-visible workflow

Audit side:

```bash
sciunit create audit-kernel
sciunit open audit-kernel
```

Run the notebook with the audit kernel. After commit, Sciunit prints a shared key.

Repeat side:

```bash
sciunit open <copy-code>
sciunit unlock e1 --key <shared-key>
sciunit repeat e1
```

For notebook replay with the repeat kernel, run `unlock` first and then use the repeat kernel normally.

The repeat kernel uses `sciunit given {connection_file} repeat latest ...` in the
repo kernelspec, so fresh installations target the most recent Sciunit execution.
During installation, `install.sh` inserts the local `repeat-handler.py` path before
registering the kernelspec with Jupyter.

If a protected execution has not been unlocked, the repeat kernel stops before replay
and prints an actionable unlock message. The message tells the user to run:

```bash
sciunit unlock <execution id> --key <shared-key>
```

Then the user should restart the Sciunit Repeat Kernel and run the notebook again.
The detailed Sciunit error is also written to `flinc.log`.

## Scope of this implementation

Portable secret and PII protection only:

- secret examples: `SMTP_PASSWORD`, `API_KEY`, `SECRET`
- PII examples: `SMTP_EMAIL`, `YOUR_EMAIL`
- config values such as `SMTP_SERVER`, `SMTP_PORT`, `SAGE_API_URL`, and `SES_HOST`
  remain plaintext

Runtime session secret rebinding is intentionally deferred to a later phase.

## Repeat-kernel locked-package scenarios

- Protected package and no cached key: repeat stops before execution and shows the
  unlock command.
- Protected package and wrong cached key: repeat stops with the Sciunit decrypt /
  unlock failure and logs details in `flinc.log`.
- Protected package and correct cached key: Sciunit restores protected files and
  placeholder values, then repeat continues normally.
- Unprotected package: repeat continues normally with no unlock prompt.
