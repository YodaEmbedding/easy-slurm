#!/bin/bash -v

{{sbatch_options_str}}

{{vars_str}}

on_run='{{on_run}}'
on_run_resume='{{on_run_resume}}'

IS_INTERRUPTED=false
IS_FIRST_RUN=false
IS_INTERACTIVE=false

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

setup_resume() {
  begin_func "setup_resume" "$SLURM_TMPDIR"
{{setup_resume}}
}

teardown() {
  begin_func "teardown" "$SLURM_TMPDIR"
{{teardown}}
}

extract_results() {
  begin_func "extract_results" "$SLURM_TMPDIR"
{{extract_results}}
}

save_results() {
  begin_func "save_results" "$SLURM_TMPDIR"
{{save_results}}
}

status_write() {
  local status_file="$JOB_DIR/status"
  echo "$1" > "$status_file"
}

handle_interrupt() {
  status_write "interrupting"
  echo ">>> Call handle_interrupt at $(date)"
  local PROG_PID="$(< "$SLURM_TMPDIR/prog.pid")"
  kill -TERM "$PROG_PID"
  IS_INTERRUPTED=true
}

parse_args() {
  for arg in "$@"; do
    case $arg in
      -i|--interactive)
        IS_INTERACTIVE=true
        shift
        ;;
      -*|--*)
        echo "Unknown argument $arg"
        exit 1
        ;;
      *)
        echo "No positional arguments accepted"
        exit 1
        ;;
    esac
  done
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
    setup_resume
  fi
}

run() {
  status_write "running"
  begin_func "run" "$SLURM_TMPDIR/src"
  trap handle_interrupt USR1
  if [ "$IS_FIRST_RUN" = true ]; then
    cmd="$on_run"
  else
    cmd="$on_run_resume"
  fi
  eval "$cmd &"
  echo $! > "$SLURM_TMPDIR/prog.pid"
  wait
}

finish() {
  begin_func "finish" "$JOB_DIR"
  if [ "$IS_INTERRUPTED" = true ]; then
    local RESULT="$(sbatch "$JOB_DIR/job.sh")"
    JOB_ID="$(sed 's/^Submitted batch job \([0-9]\+\)$/\1/' <<< "$RESULT")"
    echo "$JOB_ID" >> "$JOB_DIR/job_ids"
    status_write "incomplete"
  else
    status_write "completed"
  fi
}

initialize() {
  init_vars
  status_write "initializing"
  extract_results
  extract_data
  run_setup
}

finalize() {
  status_write "finalizing"
  teardown
  save_results
  finish
}

main() {
  parse_args "$@"
  initialize
  if [ "$IS_INTERACTIVE" = true ]; then
    status_write "interacting"
    trap finalize EXIT
  else
    run
    finalize
  fi
}

main "$@"
