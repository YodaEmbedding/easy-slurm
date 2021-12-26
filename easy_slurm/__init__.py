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

begin_func() {
  local func_name="$1"
  local start_dir="$2"
  echo ">>> Call $func_name at $(date)"
  echo "Previous directory: $PWD"
  echo "Changing directory to: $start_dir"
  cd "$start_dir" || exit
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
  echo ">>> Call handle_interrupt at $(date)"
  local PROG_PID="$(< "$SLURM_TMPDIR/prog.pid")"
  kill -TERM "$PROG_PID"
  IS_INTERRUPTED=true
}

extract_data() {
  begin_func "extract_data" "$SLURM_TMPDIR"
  mkdir datasets
  cd datasets || exit
  tar xf "$DATASET_PATH"

  cd "$SLURM_TMPDIR" || exit
  tar xf "$JOB_DIR/assets.tar.gz"
  tar xf "$JOB_DIR/src.tar.gz"
}

run_setup() {
  begin_func "run_setup" "$SLURM_TMPDIR"
  if grep -q "new" "$JOB_DIR/status"; then
    setup
  else
    tar xf "$JOB_DIR/results.tar.gz"
    setup_continue
  fi
  mkdir -p "$SLURM_TMPDIR/results"
}

run() {
  begin_func "run" "$SLURM_TMPDIR/src"
  trap handle_interrupt USR1
  if grep -q "new" "$JOB_DIR/status"; then
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

finalize() {
  begin_func "finalize" "$SLURM_TMPDIR"
  if [ "$IS_INTERRUPTED" = true ]; then
    echo "continue" > "$JOB_DIR/status"
    local RESULT="$(sbatch "$JOB_DIR/job.sh")"
    JOB_ID="$(sed 's/^Submitted batch job \([0-9]\+\)$/\1/' <<< "$RESULT")"
    echo "$JOB_ID" >> "$JOB_DIR/job_ids"
  else
    echo "completed" > "$JOB_DIR/status"
  fi
}

extract_data
run_setup
run
teardown
save_results
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


def create_job_script(
    sbatch_options: dict[str, Any],
    on_run: str,
    on_continue: str,
    setup: str,
    setup_continue: str,
    teardown: str,
    job_dir: str,
    dataset_path: str,
):
    vars_str = VARS_TEMPLATE.format(
        job_dir=job_dir,
        dataset_path=dataset_path,
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
    fix_path = lambda x: os.path.abspath(os.path.expandvars(x))
    job_root = fix_path(job_root)
    src = fix_path(src)
    assets = fix_path(assets)
    dataset = fix_path(dataset)

    now = datetime.now()
    datestamp = now.strftime("%Y-%m-%d_%H-%M-%S_%f")[:-3]
    job_name = sbatch_options.get("job-name", "untitled")
    job_dir = f"{job_root}/{datestamp}_{job_name}"
    os.makedirs(job_dir, exist_ok=True)

    _create_tar_dir(src, f"{job_dir}/src.tar.gz", "src")
    _create_tar_dir(assets, f"{job_dir}/assets.tar.gz", "assets")

    job_script_str = create_job_script(
        sbatch_options=sbatch_options,
        on_run=on_run,
        on_continue=on_continue,
        setup=setup,
        setup_continue=setup_continue,
        teardown=teardown,
        job_dir=job_dir,
        dataset_path=dataset,
    )

    with open(f"{job_dir}/job.sh", "w") as f:
        print(job_script_str, file=f)

    st = os.stat(f"{job_dir}/job.sh")
    os.chmod(f"{job_dir}/job.sh", st.st_mode | stat.S_IEXEC)

    with open(f"{job_dir}/status", "w") as f:
        print("new", file=f)

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


def _create_tar_dir(src, dst, root_name):
    transform = fr"s/^\./{root_name}/"
    subprocess.run(
        ["tar", "czf", dst, "-C", src, ".", "--transform", transform],
        check=True,
    )
