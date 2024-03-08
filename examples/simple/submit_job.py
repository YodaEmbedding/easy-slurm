import easy_slurm

easy_slurm.submit_job(
    job_dir="$HOME/.local/share/easy_slurm/{date}-{job_name}",
    src=["./src", "./assets"],
    setup="""
        # Setup the environment:
        module load python/3.9
        virtualenv --no-download "$SLURM_TMPDIR/env"
        source "$SLURM_TMPDIR/env/bin/activate"
        pip install --no-index --upgrade pip
        pip install --no-index -r "$SLURM_TMPDIR/src/requirements.txt"

        # Create/link output results directory:
        mkdir -p "$JOB_DIR/results"
        ln -s "$JOB_DIR/results" "$SLURM_TMPDIR/results"
    """,
    setup_resume="""
        setup
    """,
    on_run="cd src && python main.py",
    on_run_resume="cd src && python main.py --resume",
    teardown="""
        # Do any cleanup tasks here.
    """,
    sbatch_options={
        "job-name": "example-simple",
        "account": "def-ibajic",
        "time": "0:03:00",
        "nodes": "1",
        "ntasks-per-node": "1",
        "cpus-per-task": "1",
        "mem": "4000M",
    },
)
