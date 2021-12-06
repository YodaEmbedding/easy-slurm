import os
import shutil
import tempfile
from glob import glob

import numpy as np
import toml

import easy_slurm as ezs

HOURS = 12

DEFAULT_CONFIG = {
    "experiment": "no-z",
    # "experiment": "base",
    "comment": "",
    "time-slice": f"{HOURS}h",
    "model": "cheng2020-anchor",
    # "model": "bmshj2018-hyperprior",
    # "model": "bmshj2018-factorized",
    "dataset": "../datasets/vimeo90k_compressai",
    "num-workers": 6,
    "seed": 1234,
    "epochs": 100,
    "batch-size": 8,
    "test-batch-size": 8,
    "learning-rate": 1e-4,
    "aux-learning-rate": 1e-3,
    "lambda": 1e-2,
    "patch-size": [256, 256],
    "clip_max_norm": 1.0,
}


def write_configs():
    key = "lambda"
    values = np.logspace(-3, -1, num=7)
    for value in values:
        config = dict(DEFAULT_CONFIG)
        config[key] = round(float(value), 4)
        terms = [
            f"e={config['experiment']}",
            f"m={config['model']}",
            f"lm={config['lambda']:.4f}",
            f"lr={config['learning-rate']}",
            f"b={config['batch-size']}",
            f"t={config['time-slice']}",
            f"c={config['comment']}",
        ]
        basename = ",".join(terms)
        with open(f"configs/{basename}.toml", "w") as f:
            toml.dump(config, f=f)


def submit_job(config_path):
    filename, _ = os.path.splitext(os.path.basename(config_path))
    job_name = filename

    print(f"Submitting {filename}...")

    with tempfile.TemporaryDirectory() as assets_dir:
        shutil.copy2(config_path, f"{assets_dir}/config.toml")

        ezs.submit_job(
            job_root="/scratch/mulhaq/cache/easy_slurm",
            src="/scratch/mulhaq/src/compressai-custom-experiments-cheng2020-without-side-information",
            # src="/scratch/mulhaq/src/compressai-custom-base",
            assets=assets_dir,
            dataset="/scratch/mulhaq/datasets/vimeo90k_compressai.tar.gz",
            on_run="python main.py",
            on_continue="python main.py --continue",
            setup=r"""
                module load python/3.9
                virtualenv --no-download "$SLURM_TMPDIR/env"
                source "$SLURM_TMPDIR/env/bin/activate"
                pip install --no-index --upgrade pip
                pip install --no-index -r "$SLURM_TMPDIR/src/requirements.txt"
                pip install --no-index toml
                pip install -e "$SLURM_TMPDIR/src"
                # git clone --depth 1 https://github.com/InterDigitalInc/CompressAI "$SLURM_TMPDIR/compressai"
                # pip install -e "$SLURM_TMPDIR/compressai"
            """,
            teardown=r"""
                cd "$SLURM_TMPDIR/src"
                cp checkpoint.pth.tar checkpoint_"$(date '+%Y-%m-%d_%H-%M-%S_%3N')".pth.tar
                cp checkpoint_best_loss.pth.tar checkpoint_best_loss_"$(date '+%Y-%m-%d_%H-%M-%S_%3N')".pth.tar
                mv *.pth.tar "$SLURM_TMPDIR/results/"
            """,
            setup_continue=r"""
                setup
                cd "$SLURM_TMPDIR"
                cp "$SLURM_TMPDIR"/results/*.pth.tar "$SLURM_TMPDIR/src/"
            """,
            sbatch_options={
                "job-name": job_name,
                "account": "def-ibajic",
                "time": f"{HOURS}:00:00",
                "gres": "gpu:1",
                "nodes": "1",
                "ntasks-per-node": "1",
                "cpus-per-task": "6",
                "mem": "32000M",
            },
        )

    print(f"Submitted {job_name}.")


def submit_jobs():
    for config_path in sorted(glob("configs/*.toml")):
        submit_job(config_path)


def main():
    os.makedirs("configs", exist_ok=True)
    write_configs()
    submit_jobs()


if __name__ == "__main__":
    main()
