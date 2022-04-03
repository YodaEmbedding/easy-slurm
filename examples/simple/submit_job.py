import easy_slurm

easy_slurm.submit_job(
    job_dir="$HOME/.local/share/easy_slurm/example-simple",
    src="./src",
    assets="./assets",
    dataset="./data.tar.gz",
    on_run="python main.py",
    on_run_resume="python main.py --resume",
    setup="""
        module load python/3.9
        virtualenv --no-download "$SLURM_TMPDIR/env"
        source "$SLURM_TMPDIR/env/bin/activate"
        pip install --no-index --upgrade pip
        pip install --no-index -r "$SLURM_TMPDIR/src/requirements.txt"
    """,
    teardown="""
    """,
    setup_resume="""
        setup
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
