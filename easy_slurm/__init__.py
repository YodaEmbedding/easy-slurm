"""
# Easy Slurm

Helps users submit robust jobs to slurm using a python/bash interface.

 - Freezes source code and assets by copying to separate `JOB_DIR`.
 - Copies data to local filesystem of compute node (`SLURM_TMPDIR`)
   for performance.
 - Exposes hooks for custom bash code: `setup`, `setup_continue`,
   `on_run`, `on_continue`, and `teardown`.
 - Interrupts running worker process before job time runs out.
 - Auto-saves results back to `JOB_DIR`.
 - On continuing an incomplete run, extracts intermediate saved results
   and runs `*_continue` hooks.

## Details

### status

`status` represents a state machine.

On a given run, it goes through the steps:

```
new/incomplete
initializing
running
[interrupting]
finalizing
completed/incomplete
```

If the current run successfully completes, `status` ends with
`completed`. Otherwise, if it is interrupted, `status` includes
`interrupting` and ends with `incomplete`.
"""


import os
import re
import stat
import subprocess
from datetime import datetime
from textwrap import dedent, indent
from typing import Any


JOB_SCRIPT_TEMPLATE = r"""
#!/bin/bash -v

{{sbatch_options_str}}

{{vars_str}}

on_run="{{on_run}}"
on_continue="{{on_continue}}"

IS_INTERRUPTED=false
IS_FIRST_RUN=false

begin_func() {
  local func_name="$1"
  local start_dir="$2"
  echo ">>> Call $func_name at $(date)"
  echo "Previous directory: $PWD"
  echo "Changing directory to: $start_dir"
  cd "$start_dir" || exit 1
  echo "Changed directory to: $PWD"
}

setup() {
  begin_func "setup" "$SLURM_TMPDIR"
{{setup}}
}

setup_continue() {
  begin_func "setup_continue" "$SLURM_TMPDIR"
{{setup_continue}}
}

teardown() {
  begin_func "teardown" "$SLURM_TMPDIR"
{{teardown}}
}

handle_interrupt() {
  echo "interrupting" > "$JOB_DIR/status"
  echo ">>> Call handle_interrupt at $(date)"
  local PROG_PID="$(< "$SLURM_TMPDIR/prog.pid")"
  kill -TERM "$PROG_PID"
  IS_INTERRUPTED=true
}

init_vars() {
  if grep -q "new" "$JOB_DIR/status"; then
    IS_FIRST_RUN=true
  elif grep -q "incomplete" "$JOB_DIR/status"; then
    IS_FIRST_RUN=false
  else
    echo "Status not new or incomplete."
    exit 1
  fi
}

extract_data() {
  begin_func "extract_data" "$SLURM_TMPDIR"
  tar xf "$JOB_DIR/assets.tar.gz"
  tar xf "$JOB_DIR/src.tar.gz"
  mkdir -p "$SLURM_TMPDIR/datasets"
  cd "$SLURM_TMPDIR/datasets" || exit 1
  tar xf "$DATASET_PATH"
}

run_setup() {
  begin_func "run_setup" "$SLURM_TMPDIR"
  if [ "$IS_FIRST_RUN" = true ]; then
    setup
  else
    tar xf "$JOB_DIR/results.tar.gz"
    setup_continue
  fi
  mkdir -p "$SLURM_TMPDIR/results"
}

run() {
  echo "running" > "$JOB_DIR/status"
  begin_func "run" "$SLURM_TMPDIR/src"
  trap handle_interrupt USR1
  if [ "$IS_FIRST_RUN" = true ]; then
    cmd="$on_run"
  else
    cmd="$on_continue"
  fi
  # bash -c "echo $$ > '$SLURM_TMPDIR/prog.pid'; exec $cmd"
  eval "$cmd &"
  echo $! > "$SLURM_TMPDIR/prog.pid"
  wait
}

save_results() {
  begin_func "save_results" "$SLURM_TMPDIR"
  tar czf results.tar.gz results
  mv results.tar.gz "$JOB_DIR/"
}

finish() {
  begin_func "finish" "$JOB_DIR"
  if [ "$IS_INTERRUPTED" = true ]; then
    local RESULT="$(sbatch "$JOB_DIR/job.sh")"
    JOB_ID="$(sed 's/^Submitted batch job \([0-9]\+\)$/\1/' <<< "$RESULT")"
    echo "$JOB_ID" >> "$JOB_DIR/job_ids"
    echo "incomplete" > "$JOB_DIR/status"
  else
    echo "completed" > "$JOB_DIR/status"
  fi
}

initialize() {
  init_vars
  echo "initializing" > "$JOB_DIR/status"
  extract_data
  run_setup
}

finalize() {
  echo "finalizing" > "$JOB_DIR/status"
  teardown
  save_results
  finish
}

initialize
run
finalize
"""

JOB_SCRIPT_TEMPLATE = (
    JOB_SCRIPT_TEMPLATE.strip("\n")
    .replace("{{", "<LBRACE>")
    .replace("}}", "<RBRACE>")
    .replace("{", "{{")
    .replace("}", "}}")
    .replace("<LBRACE>", "{")
    .replace("<RBRACE>", "}")
)

VARS_TEMPLATE = r"""
JOB_DIR={job_dir}
DATASET_PATH={dataset_path}
"""

VARS_TEMPLATE = VARS_TEMPLATE.strip("\n")


def submit_job(
    job_root: str,
    src: str,
    assets: str,
    dataset: str,
    on_run: str,
    on_continue: str,
    setup: str,
    setup_continue: str,
    teardown: str,
    sbatch_options: dict[str, Any],
):
    """Submits job.

    Creates job directory with frozen assets and submits job to slurm.
    """
    job_name = sbatch_options.get("job-name", "untitled")

    job_dir = create_job_dir(
        job_name=job_name,
        job_root=job_root,
        src=src,
        assets=assets,
    )

    create_job_script(
        filename=f"{job_dir}/job.sh",
        sbatch_options=sbatch_options,
        on_run=on_run,
        on_continue=on_continue,
        setup=setup,
        setup_continue=setup_continue,
        teardown=teardown,
        job_dir=job_dir,
        dataset=dataset,
    )

    result = subprocess.run(
        ["sbatch", f"{job_dir}/job.sh"],
        check=True,
        capture_output=True,
        text=True,
    )

    m = re.match(r"^Submitted batch job (\d+)$", result.stdout)
    job_id = int(m.group(1))

    with open(f"{job_dir}/job_ids", "w") as f:
        print(job_id, file=f)


def create_job_script(
    filename: str,
    sbatch_options: dict[str, Any],
    on_run: str,
    on_continue: str,
    setup: str,
    setup_continue: str,
    teardown: str,
    job_dir: str,
    dataset: str,
):
    """Creates job script file at given path."""
    job_script_str = create_job_script_source(
        sbatch_options=sbatch_options,
        on_run=on_run,
        on_continue=on_continue,
        setup=setup,
        setup_continue=setup_continue,
        teardown=teardown,
        job_dir=job_dir,
        dataset=dataset,
    )

    with open(filename, "w") as f:
        print(job_script_str, file=f)

    st = os.stat(filename)
    os.chmod(filename, st.st_mode | stat.S_IEXEC)


def create_job_script_source(
    sbatch_options: dict[str, Any],
    on_run: str,
    on_continue: str,
    setup: str,
    setup_continue: str,
    teardown: str,
    job_dir: str,
    dataset: str,
) -> str:
    """Returns source for job script."""
    job_dir = _expand_path(job_dir)
    dataset = _expand_path(dataset)

    vars_str = VARS_TEMPLATE.format(
        job_dir=job_dir,
        dataset_path=dataset,
    )

    fix_indent = lambda x: indent(dedent(x.strip("\n")), "  ").rstrip("\n")
    setup = fix_indent(setup)
    setup_continue = fix_indent(setup_continue)
    teardown = fix_indent(teardown)

    cleanup_seconds = 120
    sbatch_options = dict(sbatch_options)
    sbatch_options["signal"] = f"B:USR1@{cleanup_seconds}"
    sbatch_options["output"] = f"{job_dir}/slurm_jobid%j_%x.out"

    sbatch_options_str = "\n".join(
        f"#SBATCH --{k}={v}" for k, v in sbatch_options.items()
    )

    return JOB_SCRIPT_TEMPLATE.format(
        sbatch_options_str=sbatch_options_str,
        vars_str=vars_str,
        on_run=on_run,
        on_continue=on_continue,
        setup=setup,
        setup_continue=setup_continue,
        teardown=teardown,
    )


def create_job_dir(
    job_name: str,
    job_root: str,
    src: str,
    assets: str,
) -> str:
    """Creates job directory and freezes all necessary files.

    Returns:
        Path to the newly created job directory.
    """
    job_root = _expand_path(job_root)
    src = _expand_path(src)
    assets = _expand_path(assets)

    now = datetime.now()
    datestamp = now.strftime("%Y-%m-%d_%H-%M-%S_%f")[:-3]
    job_dir = f"{job_root}/{datestamp}_{job_name}"
    os.makedirs(job_dir, exist_ok=True)

    _create_tar_dir(src, f"{job_dir}/src.tar.gz", "src")
    _create_tar_dir(assets, f"{job_dir}/assets.tar.gz", "assets")

    with open(f"{job_dir}/status", "w") as f:
        print("new", file=f)

    return job_dir


def _expand_path(path: str) -> str:
    return os.path.abspath(os.path.expandvars(path))


def _create_tar_dir(src, dst, root_name):
    transform = fr"s/^\./{root_name}/"
    subprocess.run(
        ["tar", "czf", dst, "-C", src, ".", "--transform", transform],
        check=True,
    )
