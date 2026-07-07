# Repeat Kernel Import Path Fix

## Issue

The modified FLINC repeat kernel launched replayed notebooks with Python safe-path behavior enabled in two places:

- `repeat-kernel/kernel.json` passed `-P` to `ipykernel_launcher`.
- `repeat-handler.py` set `PYTHONSAFEPATH=1` in the subprocess environment.

This differs from the original FLINC repeat kernel, which launches `ipykernel_launcher` without `-P` and does not set `PYTHONSAFEPATH`.

## Impact

Python safe-path mode removes the current working directory from `sys.path`. During repeat, the CDE package may correctly contain notebook-local modules next to the notebook, but imports still fail. Example:

```python
from CustomTriggers import smoke_detect
```

failed with:

```text
ModuleNotFoundError: No module named 'CustomTriggers'
```

even though the repeat package contained:

```text
cde-root/home/jovyan/work/SciDx Streaming: Disaster Alert/CustomTriggers/smoke_detect.py
```

Any notebook that imports local project files, helper packages, or modules captured next to the notebook can hit the same failure.

## Fix

The repeat launch path now preserves normal notebook import semantics:

- Remove `-P` from `repeat-kernel/kernel.json`.
- Do not set `PYTHONSAFEPATH` in `repeat-handler.py`.
- Defensively strip stale `-P` arguments in `repeat-handler.py` so older Jupyter server/kernel state cannot keep passing safe-path mode after the kernelspec is updated.

## Verification

A normal no-`-P` launch from the repeated CDE working directory includes the current directory in `sys.path`, making notebook-local modules importable:

```text
sys.path[0] == ''
CustomTriggers found: True
import ok
```

After updating the code, all existing repeat kernels must be shut down and restarted. A running repeat process cannot pick up changes to `repeat-handler.py` or the installed kernelspec.
