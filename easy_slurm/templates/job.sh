#!/bin/bash -v

{{sbatch_options_str}}

{{vars_str}}

on_run='{{on_run}}'
on_run_resume='{{on_run_resume}}'

IS_INTERRUPTED=false
IS_FIRST_RUN=false
IS_INTERACTIVE=false
RESUBMIT_COUNT=0

begin_func() {
  local func_name="$1"
  local start_dir="$2"
  echo ">>> Call $func_name at $(date)"
  cd "$start_dir" || exit 1
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

serialize_status() {
  echo "status=$1"
  echo "easy_slurm_version=$EASY_SLURM_VERSION"
  echo "resubmit_count=$RESUBMIT_COUNT"
}

status_write() {
  local status_file="$JOB_DIR/status"
  serialize_status "$1" > "$status_file"
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
  local status_file="$JOB_DIR/status"
  if grep -q 'status\s*=\s*new' "$status_file"; then
    IS_FIRST_RUN=true
  elif grep -q 'status\s*=\s*incomplete' "$status_file"; then
    IS_FIRST_RUN=false
  else
    echo "Status not new or incomplete."
    exit 1
  fi
  RESUBMIT_COUNT="$(sed -n 's/^resubmit_count=\(.*\)$/\1/p' "$status_file")"
}

extract_data() {
  begin_func "extract_data" "$SLURM_TMPDIR"
  tar xf "$JOB_DIR/src.tar.gz"
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
  begin_func "run" "$SLURM_TMPDIR"
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

resubmit_job() {
  local RESULT="$(sbatch "$JOB_DIR/job.sh")"
  local JOB_ID="$(sed 's/^Submitted batch job \([0-9]\+\)$/\1/' <<< "$RESULT")"
  echo "$JOB_ID" >> "$JOB_DIR/job_ids"
  RESUBMIT_COUNT="$(( RESUBMIT_COUNT + 1 ))"
}

finish() {
  begin_func "finish" "$JOB_DIR"
  if [ "$IS_INTERRUPTED" = true ]; then
    if (( RESUBMIT_COUNT < RESUBMIT_LIMIT )); then
      resubmit_job
    fi
    status_write "incomplete"
  else
    status_write "completed"
  fi
}

initialize() {
  init_vars
  status_write "initializing"
  extract_data
  run_setup
}

finalize() {
  status_write "finalizing"
  teardown
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
