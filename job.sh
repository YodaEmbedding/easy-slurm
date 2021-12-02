#!/usr/bin/env bash

#SBATCH --job-name=example
#SBATCH --account=def-ibajic
#SBATCH --time=3:00:00
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=32000M
#SBATCH --signal=B:USR1@120

JOB_DIR=
DATASET_PATH=

on_run="python main.py"
on_continue="python main.py --continue"

IS_INTERRUPTED=false

setup() {
  cd "$SLURM_TMPDIR"
  git clone --depth 1 https://github.com/InterDigitalInc/CompressAI "$SLURM_TMPDIR/compressai"
  module load python/3.9
  virtualenv --no-download "$SLURM_TMPDIR/env"
  source "$SLURM_TMPDIR/env/bin/activate"
  pip install --no-index --upgrade pip
  pip install --no-index -r requirements.txt
  pip install -e "$SLURM_TMPDIR/compressai"
}

setup_continue() {
  cd "$SLURM_TMPDIR"
  setup
  cd "$SLURM_TMPDIR"
  mv results/logs src/
}

teardown() {
  cd "$SLURM_TMPDIR"
  mv "$SLURM_TMPDIR/src/logs" "$SLURM_TMPDIR/results/"
}

handle_interrupt() {
  local PROG_PID="$(< "$SLURM_TMPDIR/prog.pid")"
  kill -TERM "$PROG_PID"
  IS_INTERRUPTED=true
}

extract_data() {
  cd "$SLURM_TMPDIR"
  mkdir datasets
  cd datasets
  tar xf "$DATASET_PATH"

  cd "$SLURM_TMPDIR"
  tar xf "$JOB_DIR/assets.tar.gz"
  tar xf "$JOB_DIR/src.tar.gz"
}

run_setup() {
  cd "$SLURM_TMPDIR"
  if grep -q "new" "$JOB_DIR/status"; then
    setup
  else
    tar xf "$JOB_DIR/results.tar.gz"
    setup_continue
  fi
}

run() {
  cd "$SLURM_TMPDIR"
  mkdir results
  cd "$SLURM_TMPDIR/src"
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
  cd "$SLURM_TMPDIR"
  tar czf results.tar.gz results
  mv results.tar.gz "$JOB_DIR/"
}

finalize() {
  if [ "$IS_INTERRUPTED" = true ]; then
    echo "continue" > "$JOB_DIR/status"
    JOB_ID="$(sbatch \
      --job-name="$SLURM_JOB_NAME" \
      --output="$JOB_DIR/slurm_jobid%j_%x.out" \
      "$JOB_DIR/job.sh"
    )"
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
