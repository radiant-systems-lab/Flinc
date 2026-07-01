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

## Scope of this implementation

Portable secret and PII protection only:

- secret examples: `SMTP_PASSWORD`, `API_KEY`, `SECRET`
- PII examples: `SMTP_EMAIL`, `YOUR_EMAIL`
- config values such as `SMTP_SERVER`, `SMTP_PORT`, `SAGE_API_URL`, and `SES_HOST`
  remain plaintext

Runtime session secrets are intentionally deferred to a later phase.
