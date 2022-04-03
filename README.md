# Easy Slurm

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT) [![PyPI](https://img.shields.io/pypi/v/easy-slurm)](https://pypi.org/project/easy-slurm)

Easily manage and submit robust jobs to Slurm using Python and Bash.

## Features

 - **Freezes** source code and assets by copying to separate `$JOB_DIR`.
 - **Auto-submits** another job if current job times out.
 - **Exposes hooks** for custom bash code: `setup`/`setup_resume`, `on_run`/`on_run_resume`, and `teardown`.
 - [**Format job names**](#formatting) using parameters from config files.
 - **Interactive** jobs supported for easy debugging.

## Installation

```bash
pip install easy-slurm
```

## Usage

To submit a job, simply fill in the various parameters shown in the example below.

```python
import easy_slurm

easy_slurm.submit_job(
    job_dir="$HOME/jobs/{date:%Y-%m-%d}-{job_name}",
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

All job files will be kept in the `job_dir` directory. Provide directory paths to `src` and `assets` -- these will be archived and copied to the `job_dir` directory. Provide a file path to an archive containing the `dataset`. Also provide Bash code in the hooks, which will be run in the following order:

```
setup / setup_resume
on_run / on_run_resume
teardown
```

Full examples can be found [here](./examples), including a [simple example](./examples/simple) to run "training epochs" on a cluster.

### Formatting

One useful feature is formatting paths using custom template strings:
```python
easy_slurm.submit_job(
    job_dir="$HOME/jobs/{date:%Y-%m-%d}-{job_name}",
)
```

The job names can be formatted using a config dictionary:
```python
job_name = easy_slurm.format.format_with_config(
    "bs={hp.batch_size:04},lr={hp.lr:.1e}",
    config={"hp": {"batch_size": 32, "lr": 1e-2}},
)

easy_slurm.submit_job(
    job_dir="$HOME/jobs/{date:%Y-%m-%d}-{job_name}",
    sbatch_options={
        "job-name": job_name,  # equals "bs=0032,lr=1.0e-02"
        ...
    },
    ...
)
```

This helps in automatically creating descriptive, human-readable job names.

See documentation for more information and examples.

### Config API

Coming soon!

Jobs and hyperparameters can be fully configured and composed using dictionaries or YAML files.

```yaml
# job.yaml

job_dir: "$HOME/.local/share/easy_slurm/example-simple"
src: "./src"
assets: "./assets"
dataset: "./data.tar.gz"
on_run: "python main.py"
on_run_resume: "python main.py --resume"
setup: |
  module load python/3.9
  virtualenv --no-download "$SLURM_TMPDIR/env"
  source "$SLURM_TMPDIR/env/bin/activate"
  pip install --no-index --upgrade pip
  pip install --no-index -r "$SLURM_TMPDIR/src/requirements.txt"
teardown: |

setup_resume: |
  setup
sbatch_options:
  job-name: "example-simple"
  account: "def-ibajic"
  time: "0:03:00"
  nodes: 1
  ntasks-per-node: 1
  cpus-per-task: 1
  mem: "4000M"
```

```yaml
# hparams.yaml

hp:
  batch_size: 16
  lr: 1e-2
```
