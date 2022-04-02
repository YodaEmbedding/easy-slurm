import os
import re
import stat
import subprocess
from datetime import datetime
from textwrap import dedent, indent
from typing import Any

from . import __version__
from .templates import (
    EXTRACT_RESULTS,
    JOB_INTERACTIVE_TEMPLATE,
    JOB_SCRIPT_TEMPLATE,
    SAVE_RESULTS,
    VARS_TEMPLATE,
)


def submit_job(
    job_root: str,
    src: str,
    assets: str,
    dataset: str,
    on_run: str,
    on_run_resume: str,
    setup: str,
    setup_resume: str,
    teardown: str,
    sbatch_options: dict[str, Any],
    cleanup_seconds: int = 120,
    submit: bool = True,
    interactive: bool = False,
    resubmit_limit: int = 64,
    results_sync_method: str = "symlink",
) -> str:
    """Submits job.

    Creates job directory with frozen assets and submits job to slurm.

    Args:
        job_root (str):
            Path to directory where a time-stamped `$JOB_DIR` will be
            created to store all job files including `src.tar`,
            `assets.tar`, auto-generated `job.sh`, and results.
            Note that the `dataset` will not be copied and will remain
            in its original path.
        src (str):
            Path to directory containing only source code.
            These will be archived in `$JOB_DIR/src.tar` and
            extracted during job run into `$SLURM_TMPDIR/src`.
        assets (str):
            Path to directory containing additional assets.
            These will be archived in `$JOB_DIR/assets.tar` and
            extracted during job run into `$SLURM_TMPDIR/assets`.
        dataset (str):
            Path to `.tar` archive of dataset. This will be copied and
            extracted on the local filesystem of the compute node,
            `$SLURM_TMPDIR`.
        on_run (str):
            Bash code executed in "on_run" stage, but only for new jobs
            that are running for the first time.
            Must be a single command only.
            Optionally, the command may gracefully handle interrupts.
        on_run_resume (str):
            Bash code executed in "on_run" stage, but only for jobs that
            are resuming from previous incomplete runs.
            Must be a single command only.
            Optionally, the command may gracefully handle interrupts.
        setup (str):
            Bash code executed in "setup" stage, but only for new jobs
            that are running for the first time.
        setup_resume (str):
            Bash code executed in "setup" stage, but only for jobs that
            are resuming from previous incomplete runs.
            To reuse the code from `setup`, simply set this to
            `"setup"`, which calls the code inside the `setup` function.
        teardown (str):
            Bash code executed in "teardown" stage.
        sbatch_options (dict[str, Any]):
            Dictionary of options to pass to sbatch.
        cleanup_seconds (int):
            Interrupts a job n seconds before timeout to run cleanup
            tasks (teardown, save_results, auto-schedule new job).
            Default is 120 seconds.
        submit (bool):
            Submit created job to scheduler. Set this to `False` if you
            are manually submitting the created `$JOB_DIR` later.
            Default is `True`.
        interactive (bool):
            Run as a blocking interactive job. Default is `False`.
        resubmit_limit (int):
            Maximum number of times to auto-submit a job for "resume".
            (Not entirely unlike submitting a resume for a job.)
            Default is 64 resubmissions.
        results_sync_method (str):
            Choices: "rsync", "symlink", or "targz".
             - rsync: Sync results directory via rsync.
             - symlink: Directly symlink results directory.
             - targz: Extract/archive results directory into .tar.gz.
            Default is `"symlink"`.

        Returns:
            Path to the newly created job directory.
    """
    job_name = sbatch_options.get("job-name", "untitled")

    job_dir = create_job_dir(
        job_name=job_name,
        job_root=job_root,
        src=src,
        assets=assets,
    )

    job_path = f"{job_dir}/job.sh"
    job_script_str = create_job_script_source(
        sbatch_options=sbatch_options,
        on_run=on_run,
        on_run_resume=on_run_resume,
        setup=setup,
        setup_resume=setup_resume,
        teardown=teardown,
        job_dir=job_dir,
        dataset=dataset,
        cleanup_seconds=cleanup_seconds,
        resubmit_limit=resubmit_limit,
        results_sync_method=results_sync_method,
    )
    _write_script(job_path, job_script_str)

    job_interactive_path = f"{job_dir}/job_interactive.sh"
    job_interactive_script_str = create_job_interactive_script_source(
        sbatch_options=sbatch_options,
        job_path=job_path,
        job_dir=job_dir,
        cleanup_seconds=cleanup_seconds,
    )
    _write_script(job_interactive_path, job_interactive_script_str)

    if submit:
        submit_job_dir(job_dir, interactive)

    return job_dir


def create_job_script_source(
    sbatch_options: dict[str, Any],
    on_run: str,
    on_run_resume: str,
    setup: str,
    setup_resume: str,
    teardown: str,
    job_dir: str,
    dataset: str,
    cleanup_seconds: int,
    resubmit_limit: int,
    results_sync_method: str,
) -> str:
    """Returns source for job script."""
    job_dir = _expand_path(job_dir)
    dataset = _expand_path(dataset)

    vars_str = VARS_TEMPLATE.format(
        easy_slurm_version=__version__,
        job_dir=job_dir,
        dataset_path=dataset,
        resubmit_limit=resubmit_limit,
    )

    extract_results = EXTRACT_RESULTS[results_sync_method]
    save_results = SAVE_RESULTS[results_sync_method]

    setup = _fix_indent(setup, 1)
    setup_resume = _fix_indent(setup_resume, 1)
    teardown = _fix_indent(teardown, 1)
    extract_results = _fix_indent(extract_results, 1)
    save_results = _fix_indent(save_results, 1)

    fix_quotes = lambda x: _quote_single_quotes(x.strip())
    on_run = fix_quotes(on_run)
    on_run_resume = fix_quotes(on_run_resume)

    sbatch_options_str = _sbatch_options_to_str(
        sbatch_options, job_dir, cleanup_seconds
    )

    return JOB_SCRIPT_TEMPLATE.format(
        sbatch_options_str=sbatch_options_str,
        vars_str=vars_str,
        on_run=on_run,
        on_run_resume=on_run_resume,
        setup=setup,
        setup_resume=setup_resume,
        teardown=teardown,
        extract_results=extract_results,
        save_results=save_results,
    )


def create_job_interactive_script_source(
    sbatch_options: dict[str, Any],
    job_dir: str,
    job_path: str,
    cleanup_seconds: int,
) -> str:
    """Returns source for job script."""
    job_dir = _expand_path(job_dir)
    job_path = _expand_path(job_path)

    sbatch_options_str = _sbatch_options_to_str(
        sbatch_options, job_dir, cleanup_seconds
    )

    return JOB_INTERACTIVE_TEMPLATE.format(
        sbatch_options_str=sbatch_options_str,
        job_path=job_path,
    )


def create_job_dir(
    job_name: str,
    job_root: str,
    src: str,
    assets: str,
) -> str:
    """Creates job directory and freezes all necessary files.

    Returns:
        Path to the newly created job directory.
    """
    job_root = _expand_path(job_root)
    src = _expand_path(src)
    assets = _expand_path(assets)

    now = datetime.now()
    datestamp = now.strftime("%Y-%m-%d_%H-%M-%S_%f")[:-3]
    job_dir = f"{job_root}/{datestamp}_{job_name}"
    os.makedirs(job_dir, exist_ok=True)

    _create_tar_dir(src, f"{job_dir}/src.tar.gz", "src")
    _create_tar_dir(assets, f"{job_dir}/assets.tar.gz", "assets")

    with open(f"{job_dir}/status", "w") as f:
        print("new", file=f)
        print(f"easy_slurm_version={__version__}", file=f)
        print("resubmit_count=0", file=f)

    return job_dir


def submit_job_dir(job_dir: str, interactive: bool):
    """Submits a `$JOB_DIR` created by easy_slurm to slurm.

    Note that `submit_job` already does this for the user,
    except when it is called with `submit=False`.
    """
    if interactive:
        job_interactive_path = f"{job_dir}/job_interactive.sh"
        subprocess.run(
            ["srun", "--pty", "bash", "--init-file", job_interactive_path],
            check=True,
            text=True,
        )
    else:
        job_path = f"{job_dir}/job.sh"
        result = subprocess.run(
            ["sbatch", job_path],
            check=True,
            capture_output=True,
            text=True,
        )

        m = re.match(r"^Submitted batch job (\d+)$", result.stdout)
        job_id = int(m.group(1))

        with open(f"{job_dir}/job_ids", "w") as f:
            print(job_id, file=f)


def _expand_path(path: str) -> str:
    return os.path.abspath(os.path.expandvars(path))


def _create_tar_dir(src, dst, root_name):
    transform = fr"s/^\./{root_name}/"
    subprocess.run(
        ["tar", "czf", dst, "-C", src, ".", "--transform", transform],
        check=True,
    )


def _write_script(filename: str, text: str):
    with open(filename, "w") as f:
        print(text, file=f)

    st = os.stat(filename)
    os.chmod(filename, st.st_mode | stat.S_IEXEC)


def _sbatch_options_to_str(
    sbatch_options: dict[str, Any], job_dir: str, cleanup_seconds: int
) -> str:
    sbatch_options = dict(sbatch_options)
    sbatch_options["output"] = f"{job_dir}/slurm_jobid%j_%x.out"
    sbatch_options["signal"] = f"B:USR1@{cleanup_seconds}"
    return "\n".join(f"#SBATCH --{k}={v}" for k, v in sbatch_options.items())


def _quote_single_quotes(s: str) -> str:
    """Replaces ' with '"'"'."""
    return s.replace("'", """'"'"'""")


def _fix_indent(x: str, level: int = 0) -> str:
    return indent(dedent(x.strip("\n")), "  " * level).rstrip("\n")
