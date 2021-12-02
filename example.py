import easy_slurm as ezs


ezs.submit_job(
    job_root="$HOME/.local/share/easy_slurm",
    src="./test_src",
    assets="./test_assets",
    dataset="./test_data.tar.gz",
    on_run="python main.py",
    on_continue="python main.py --continue",
    setup="""
        git clone --depth 1 https://github.com/InterDigitalInc/CompressAI "$SLURM_TMPDIR/compressai"
        module load python/3.9
        virtualenv --no-download "$SLURM_TMPDIR/env"
        source "$SLURM_TMPDIR/env/bin/activate"
        pip install --no-index --upgrade pip
        pip install --no-index -r requirements.txt
        pip install -e "$SLURM_TMPDIR/compressai"
    """,
    teardown="""
        mv "$SLURM_TMPDIR/src/logs" "$SLURM_TMPDIR/results/"
    """,
    setup_continue="""
        setup
        cd "$SLURM_TMPDIR"
        mv results/logs src/
    """,
    sbatch_options={
        "job-name": "example",
        "account": "def-ibajic",
        "time": "3:00:00",
        "gres": "gpu:1",
        "nodes": "1",
        "ntasks-per-node": "1",
        "cpus-per-task": "6",
        "mem": "32000M",
    },
)
