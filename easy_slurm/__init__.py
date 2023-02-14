"""
Easy Slurm
==========

Helps users submit robust jobs to slurm using a python/bash interface.

- Freezes source code and assets by copying to separate ``JOB_DIR``.
- Copies data to local filesystem of compute node (``SLURM_TMPDIR``)
  for performance.
- Exposes hooks for custom bash code: ``setup``, ``setup_resume``,
  ``on_run``, ``on_run_resume``, and ``teardown``.
- Interrupts running worker process before job time runs out.
- Auto-saves results back to ``JOB_DIR``.
- On resuming an incomplete run, extracts intermediate saved results
  and runs ``*_resume`` hooks.

Details
-------

status
~~~~~~

``status`` represents a state machine.

On a given run, it goes through the steps:

```
new/incomplete
initializing
running
[interrupting]
finalizing
completed/incomplete
```

If the current run successfully completes, ``status`` ends with
``completed``. Otherwise, if it is interrupted, ``status`` includes
``interrupting`` and ends with ``incomplete``.
"""

__version__ = "0.2.2"

from .format import format_with_config
from .jobs import (
    create_job_dir,
    create_job_interactive_script_source,
    create_job_script_source,
    submit_job,
    submit_job_dir,
)
