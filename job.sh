#!/usr/bin/env bash

#SBATCH ...
#SBATCH --signal=B:USR1@120


JOB_DIR=
DATASET_PATH=

IS_INTERRUPTED=false

presetup_continue() {
  mv results/logs src/
}

setup() {
  git clone --depth 1 https://github.com/InterDigitalInc/CompressAI "$SLURM_TMPDIR/compressai"
  module load python/3.9
  virtualenv --no-download "$SLURM_TMPDIR/env"
  source "$SLURM_TMPDIR/env/bin/activate"
  pip install --no-index --upgrade pip
  pip install --no-index -r requirements.txt
  pip install -e "$SLURM_TMPDIR/compressai"
}

# on_run() {
#   python main.py
# }
#
# on_continue() {
#   python main.py --continue
# }

teardown() {
  mv "$SLURM_TMPDIR/src/logs" "$SLURM_TMPDIR/results/"
}

handle_interrupt() {
  local PROG_PID="$(< "$SLURM_TMPDIR/prog.pid")"
  kill -TERM $PROG_PID
  IS_INTERRUPTED=true
}


cd "$SLURM_TMPDIR"
mkdir datasets
cd datasets
tar xf "$DATASET_PATH"

cd "$SLURM_TMPDIR"
tar xf "$JOB_DIR/assets.tar.gz"
tar xf "$JOB_DIR/src.tar.gz"

if grep -q "continue" "$JOB_DIR/status"; then
  tar xf "$JOB_DIR/results.tar.gz"
  cd "$SLURM_TMPDIR"
  presetup_continue
fi

cd "$SLURM_TMPDIR"
setup

cd "$SLURM_TMPDIR/src"
trap handle_interrupt USR1
if grep -q "new" "$JOB_DIR/status"; then
  # on_run
  # bash -c 'echo $$ > "$SLURM_TMPDIR/prog.pid"; exec python main.py'
  python main.py &
else
  # on_continue
  # bash -c 'echo $$ > "$SLURM_TMPDIR/prog.pid"; exec python main.py --continue'
  python main.py --continue &
fi
echo $! > "$SLURM_TMPDIR/prog.pid"
wait

cd "$SLURM_TMPDIR"
teardown

cd "$SLURM_TMPDIR"
tar czf "$SLURM_TMPDIR/results/" results.tar.gz
mv results.tar.gz "$JOB_DIR/"

if [ $IS_INTERRUPTED = true ]; then
  echo "continue" > "$JOB_DIR/status"
  JOB_ID="$(sbatch
    --job-name="$SLURM_JOB_NAME"
    --output="$JOB_DIR/slurm_jobid%j_%x.out"
    "$JOB_DIR/job.sh"
  )"
  echo "$JOB_ID" >> "$JOB_DIR/job_ids"
else
  echo "completed" > "$JOB_DIR/status"
fi
