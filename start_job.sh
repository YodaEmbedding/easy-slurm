#!/usr/bin/env bash

SLURM_JOB_NAME="example"
JOB_ROOT="$HOME/.local/share/easy_slurm"
DATASET_PATH="$PWD/test_data.tar.gz"
SRC_PATH="$PWD/test_src"
ASSETS_PATH="$PWD/test_assets"

DATESTAMP="$(date '+%Y-%m-%d_%H-%M-%S_%3N')"
JOB_DIR="$JOB_ROOT/$DATESTAMP"

mkdir -p "$JOB_DIR"

tar czf "$JOB_DIR/src.tar.gz" -C "$SRC_PATH" . --transform 's/^\./src/'

cp job.sh "$JOB_DIR"
sed -i 's:^\(JOB_DIR=\)$:\1"'"$JOB_DIR"'":' "$JOB_DIR/job.sh"
sed -i 's:^\(DATASET_PATH=\)$:\1"'"$DATASET_PATH"'":' "$JOB_DIR/job.sh"

echo "new" > "$JOB_DIR/status"

JOB_ID="$(sbatch \
  --job-name="$SLURM_JOB_NAME" \
  --output="$JOB_DIR/slurm_jobid%j_%x.out" \
  "$JOB_DIR/job.sh"
)"
echo "$JOB_ID" > "$JOB_DIR/job_ids"
