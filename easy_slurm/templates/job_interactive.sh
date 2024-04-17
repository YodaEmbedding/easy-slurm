#!/bin/bash -v

SBATCH_OPTIONS=(
{{sbatch_options_str}}
)

CMD=(bash --init-file _job_interactive.sh)

cat <<EOF > _job_interactive.sh
#!/bin/bash -v

source {{job_path}} --interactive
EOF

srun --pty "${SBATCH_OPTIONS[@]}" "${CMD[@]}"
