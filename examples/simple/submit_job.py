import easy_slurm as ezs


ezs.submit_job(
    job_root="$HOME/.local/share/easy_slurm/example-simple",
    src="./src",
    assets="./assets",
    dataset="./data.tar.gz",
    on_run="python main.py",
    on_continue="python main.py --continue",
    setup="""
        module load python/3.9
        virtualenv --no-download "$SLURM_TMPDIR/env"
        source "$SLURM_TMPDIR/env/bin/activate"
        pip install --no-index --upgrade pip
        pip install --no-index -r "$SLURM_TMPDIR/src/requirements.txt"
    """,
    teardown="""
    """,
    setup_continue="""
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