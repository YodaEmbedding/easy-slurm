# Easy Slurm

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT) [![PyPI](https://img.shields.io/pypi/v/easy-slurm)](https://pypi.org/project/easy-slurm)

Easily manage and submit robust jobs to Slurm using Python and Bash.

## Features

 - **Freezes** source code and assets by copying to separate `JOB_DIR`.
 - Applies **performance tweaks** like copying data to local filesystem of compute node (`SLURM_TMPDIR`) for fast I/O.
 - **Exposes hooks** for custom bash code: `setup`/`setup_resume`, `on_run`/`on_run_resume`, and `teardown`.
 - Interrupts running worker process **before job time runs out**.
 - **Auto-saves results** back to `JOB_DIR`.
 - **Auto-submits** another job if current job times out.
 - **Restores** intermediate results and resumes running the `*_resume` hooks.
 - Supports **interactive** jobs for easy debugging.

## Installation

```bash
pip install easy-slurm
```

## Usage

To submit a job, simply fill in the various parameters shown in the example below.

```python
import easy_slurm

easy_slurm.submit_job(
    job_root="$HOME/.local/share/easy_slurm/example-simple",
    src="./src",
    assets="./assets",
    dataset="./data.tar.gz",
    setup="""
        virtualenv "$SLURM_TMPDIR/env"
        source "$SLURM_TMPDIR/env/bin/activate"
        pip install -r "$SLURM_TMPDIR/src/requirements.txt"
    """,
    setup_resume="""
        # Runs only on subsequent runs. Call setup and do anything else needed.
        setup
    """,
    on_run="python main.py",
    on_run_resume="python main.py --resume",
    teardown="""
        # Copy files to results directory.
        cp "$SLURM_TMPDIR/src/*.log" "$SLURM_TMPDIR/results/"
    """,
    sbatch_options={
        "job-name": "example-simple",
        "account": "your-username",
        "time": "3:00:00",
        "nodes": "1",
    },
)
```

All job files will be kept in the `job_root` directory. Provide directory paths to `src` and `assets` -- these will be archived and copied to the `job_root` directory. Provide a file path to an archive containing the `dataset`. Also provide Bash code in the hooks, which will be run in the following order:

```
setup / setup_resume
on_run / on_run_resume
teardown
```

Full examples can be found [here](./examples), including a [simple example](./examples/simple) to run "training epochs" on a cluster.

