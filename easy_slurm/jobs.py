import os
import re
import stat
import subprocess
from pathlib import Path
from textwrap import dedent, indent
from typing import Any, Sequence

from . import __version__
from .format import format_with_config
from .templates import (
    JOB_INTERACTIVE_TEMPLATE,
    JOB_SCRIPT_TEMPLATE,
    VARS_TEMPLATE,
)

__all__ = [
    "create_job_dir",
    "create_job_interactive_script_source",
    "create_job_script_source",
    "submit_job",
    "submit_job_dir",
]


def submit_job(
    job_dir: str,
    *,
    src: Sequence[str] = (),
    on_run: str = "",
    on_run_resume: str = "",
    setup: str = "",
    setup_resume: str = "",
    teardown: str = "",
    sbatch_options: dict[str, Any] = {},
    cleanup_seconds: int = 120,
    submit: bool = True,
    interactive: bool = False,
    resubmit_limit: int = 64,
) -> str:
    """Submits job.

    Creates job directory with frozen src and submits job to slurm.

    Args:
        job_dir (str):
            Path to directory to keep all job files including
            ``src.tar`` and auto-generated ``job.sh``.
        src (list[str]):
            Path to directories containing only source code.
            These will be archived in ``$JOB_DIR/src.tar`` and
            extracted during job run into ``$SLURM_TMPDIR``.
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
            To reuse the code from ``setup``, simply set this to
            ``"setup"``, which calls the code inside the ``setup``
            function.
        teardown (str):
            Bash code executed in "teardown" stage.
        sbatch_options (dict[str, Any]):
            Dictionary of options to pass to sbatch.
        cleanup_seconds (int):
            Interrupts a job n seconds before timeout to run cleanup
            tasks (teardown, auto-schedule new job).
            Default is 120 seconds.
        submit (bool):
            Submit created job to scheduler. Set this to ``False`` if
            you are manually submitting the created ``$JOB_DIR`` later.
            Default is ``True``.
        interactive (bool):
            Run as a blocking interactive job. Default is ``False``.
        resubmit_limit (int):
            Maximum number of times to auto-submit a job for "resume".
            (Not entirely unlike submitting a resume for a job.)
            Default is 64 resubmissions.

    Returns:
        Path to the newly created job directory.
    """
    job_name = sbatch_options.get("job-name", "untitled")
    job_dir = _expand_path(format_with_config(job_dir, {"job_name": job_name}))
    create_job_dir(job_dir, src)

    _write_script(
        filename=f"{job_dir}/job.sh",
        text=create_job_script_source(
            sbatch_options=sbatch_options,
            on_run=on_run,
            on_run_resume=on_run_resume,
            setup=setup,
            setup_resume=setup_resume,
            teardown=teardown,
            job_dir=job_dir,
            cleanup_seconds=cleanup_seconds,
            resubmit_limit=resubmit_limit,
        ),
    )

    _write_script(
        filename=f"{job_dir}/job_interactive.sh",
        text=create_job_interactive_script_source(
            sbatch_options=sbatch_options,
            job_path=f"{job_dir}/job.sh",
            job_dir=job_dir,
            cleanup_seconds=cleanup_seconds,
        ),
    )

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
    cleanup_seconds: int,
    resubmit_limit: int,
) -> str:
    """Returns source for job script."""
    job_dir = _expand_path(job_dir)
    fix_quotes = lambda x: _quote_single_quotes(x.strip())

    return JOB_SCRIPT_TEMPLATE.format(
        sbatch_options_str=_sbatch_options_to_str(
            sbatch_options, job_dir, cleanup_seconds
        ),
        vars_str=VARS_TEMPLATE.format(
            easy_slurm_version=__version__,
            job_dir=job_dir,
            resubmit_limit=resubmit_limit,
        ),
        on_run=fix_quotes(on_run),
        on_run_resume=fix_quotes(on_run_resume),
        setup=_fix_indent(setup, 1),
        setup_resume=_fix_indent(setup_resume, 1),
        teardown=_fix_indent(teardown, 1),
    )


def create_job_interactive_script_source(
    sbatch_options: dict[str, Any],
    job_dir: str,
    job_path: str,
    cleanup_seconds: int,
) -> str:
    """Returns source for interactive job script."""
    job_dir = _expand_path(job_dir)
    job_path = _expand_path(job_path)

    return JOB_INTERACTIVE_TEMPLATE.format(
        sbatch_options_str=_sbatch_options_to_str(
            sbatch_options, job_dir, cleanup_seconds
        ),
        job_path=job_path,
    )


def create_job_dir(job_dir: str, src: Sequence[str]):
    """Creates job directory and freezes all necessary files."""
    job_dir = _expand_path(job_dir)
    src = [_expand_path(x) for x in src]

    os.makedirs(job_dir, exist_ok=True)
    _create_tar_dir(src, f"{job_dir}/src.tar.gz")

    with open(f"{job_dir}/status", "w") as f:
        print("status=new", file=f)
        print(f"easy_slurm_version={__version__}", file=f)
        print("resubmit_count=0", file=f)


def submit_job_dir(job_dir: str, interactive: bool):
    """Submits a ``$JOB_DIR`` created by easy_slurm to slurm.

    Note that ``submit_job`` already does this for the user,
    except when it is called with ``submit=False``.
    """
    if interactive:
        job_interactive_path = f"{job_dir}/job_interactive.sh"
        cmd = ["srun", "--pty", "bash", "--init-file", job_interactive_path]
        subprocess.run(cmd, check=True, text=True)
        return

    job_path = f"{job_dir}/job.sh"
    cmd = ["sbatch", job_path]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)

    m = re.match(r"^Submitted batch job (\d+)$", result.stdout)
    job_id = int(m.group(1))

    with open(f"{job_dir}/job_ids", "w") as f:
        print(job_id, file=f)


def _expand_path(path: str) -> str:
    return "" if path == "" else os.path.abspath(os.path.expandvars(path))


def _create_tar_dir(src, dst, root_name=None):
    if not src:
        src_args = ["-T", "/dev/null"]
    else:
        src_args = [
            arg
            for srcdir in src
            for arg in ["-C", Path(srcdir).parent, Path(srcdir).name]
        ]
    cmd = ["tar", "czf", dst, *src_args]
    if root_name is not None:
        cmd.extend(["--transform", rf"s/^/{root_name}\//"])
    subprocess.run(cmd, check=True)


def _write_script(filename: str, text: str):
    with open(filename, "w") as f:
        print(text, file=f)

    st = os.stat(filename)
    os.chmod(filename, st.st_mode | stat.S_IEXEC)


def _sbatch_options_to_str(
    sbatch_options: dict[str, Any], job_dir: str, cleanup_seconds: int
) -> str:
    sbatch_options = {
        **sbatch_options,
        "output": f"{job_dir}/slurm_jobid%j_%x.out",
        "signal": f"B:USR1@{cleanup_seconds}",  # send USR1 to Bash before job end time
    }
    return "\n".join(f"#SBATCH --{k}={v}" for k, v in sbatch_options.items())


def _quote_single_quotes(s: str) -> str:
    """Replaces ' with '"'"'."""
    return s.replace("'", """'"'"'""")


def _fix_indent(x: str, level: int = 0) -> str:
    return indent(dedent(x.strip("\n")), "  " * level).rstrip("\n")
