# Easy Slurm

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT) [![PyPI](https://img.shields.io/pypi/v/easy-slurm)](https://pypi.org/project/easy-slurm)

Easily manage and submit robust jobs to Slurm using Python and Bash.

## Features

 - **Freezes** source code by copying to separate `$JOB_DIR`.
 - **Auto-submits** another job if current job times out.
 - **Exposes hooks** for custom bash code: `setup`/`setup_resume`, `on_run`/`on_run_resume`, and `teardown`.
 - [**Format job names**](#formatting) using parameters from config files.
 - **Interactive** jobs supported for easy debugging.

## Installation

```bash
pip install easy-slurm
```

## Usage

Easy Slurm provides a CLI / YAML interface, as well as a Python interface.


### Python API

To submit a job, simply fill in the various parameters shown in the example below.

```python
import easy_slurm

easy_slurm.submit_job(
    job_dir="$HOME/jobs/{date}-{job_name}",
    src=["./src", "./assets"],
    setup="""
        virtualenv "$SLURM_TMPDIR/env"
        source "$SLURM_TMPDIR/env/bin/activate"
        pip install -r "$SLURM_TMPDIR/src/requirements.txt"
    """,
    setup_resume="""
        # Runs only on subsequent runs. Call setup and do anything else needed.
        setup
    """,
    on_run="cd src && python main.py",
    on_run_resume="cd src && python main.py --resume",
    teardown="""
        # Do any cleanup tasks here.
    """,
    sbatch_options={
        "job-name": "example-simple",
        "account": "your-username",
        "time": "3:00:00",
        "nodes": "1",
    },
    resubmit_limit=64,  # Automatic resubmission limit.
)
```

All job files will be kept in the `job_dir` directory. Provide directory paths to `src` -- these will be archived and copied to the `job_dir` directory. Also provide Bash code in the hooks, which will be run in the following order:

| First run: | Subsequent runs: |
| ---------- | ---------------- |
| `setup`    | `setup_resume`   |
| `on_run`   | `on_run_resume`  |
| `teardown` | `teardown`       |

Full examples can be found [here](./examples), including a [simple example](./examples/simple) to run "training epochs" on a cluster.


### CLI / YAML Interface

Jobs can also be fully configured using YAML files. See [`examples/simple_yaml`](./examples/simple_yaml).

<table>
<tr>
<td><code>job.yaml</code></td>
</tr>
<tr>
<td>

```yaml
job_dir: "$HOME/jobs/{date}-{job_name}"
src: ["./src", "./assets"]
setup: |
  virtualenv "$SLURM_TMPDIR/env"
  source "$SLURM_TMPDIR/env/bin/activate"
  pip install -r "$SLURM_TMPDIR/src/requirements.txt"
setup_resume: |
  # Runs only on subsequent runs. Call setup and do anything else needed.
  setup
on_run: "cd src && python main.py"
on_run_resume: "cd src && python main.py --resume"
teardown: |
  # Do any cleanup tasks here.
sbatch_options:
  job-name: "example-simple"
  account: "your-username"
  time: "3:00:00"
  nodes: 1
resubmit_limit: 64  # Automatic resubmission limit.
```
</td>
</tr>
</table>

Then submit the job using:

```bash
easy-slurm --job="job.yaml"
```

One can override the parameters in the YAML file using command-line arguments. For example:

```bash
easy-slurm --job="job.yaml" --src='["./src", "./assets", "./extra"]'
```


### Formatting

One useful feature is formatting paths using custom template strings:
```python
easy_slurm.submit_job(
    job_dir="$HOME/jobs/{date:%Y-%m-%d_%H-%M-%S_%3f}-{job_name}",
)
```

The job names can be formatted using a config dictionary:
```python
easy_slurm.submit_job(
    sbatch_options={
        "job-name": "bs={hp.batch_size:04},lr={hp.lr:.1e}",
        # Equivalent to:
        # "job-name": "bs=0032,lr=1.0e-02"
    },
    config={"hp": {"batch_size": 32, "lr": 1e-2}},
)
```

This helps in automatically creating descriptive, human-readable job names.

For the CLI / YAML interface, the same can be achieved using the `--config` argument:

```bash
easy-slurm --job="job.yaml" --config="config.yaml"
```

See the [documentation] for more information and examples.

  [documentation]: https://yodaembedding.github.io/easy-slurm/
