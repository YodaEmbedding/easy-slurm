import argparse
import json
from textwrap import dedent

import yaml

from easy_slurm.jobs import submit_job


def format_help(help_text: str) -> str:
    return dedent(help_text).strip()


ARGUMENTS = [
    {
        "args": ["--job"],
        "type": str,
        "help": format_help(
            """
            Path to job config file.
            """
        ),
    },
    {
        "args": ["--job_dir"],
        "type": str,
        "help": format_help(
            """
            Path to directory to keep all job files including
            ``src.tar`` and auto-generated ``job.sh``.
            """
        ),
    },
    {
        "args": ["--src"],
        "type": json.loads,
        "help": format_help(
            """
            Path to directories containing only source code.
            These will be archived in ``$JOB_DIR/src.tar`` and
            extracted during job run into ``$SLURM_TMPDIR``.
            """
        ),
    },
    {
        "args": ["--on_run"],
        "type": str,
        "help": format_help(
            """
            Bash code executed in "on_run" stage, but only for new jobs
            that are running for the first time.
            Must be a single command only.
            Optionally, the command may gracefully handle interrupts.
            """
        ),
    },
    {
        "args": ["--on_run_resume"],
        "type": str,
        "help": format_help(
            """
        Bash code executed in "on_run" stage, but only for jobs that
        are resuming from previous incomplete runs.
        Must be a single command only.
        Optionally, the command may gracefully handle interrupts.
        """
        ),
    },
    {
        "args": ["--setup"],
        "type": str,
        "help": format_help(
            """
            Bash code executed in "setup" stage, but only for new jobs
            that are running for the first time.
            """
        ),
    },
    {
        "args": ["--setup_resume"],
        "type": str,
        "help": format_help(
            """
            Bash code executed in "setup" stage, but only for jobs that
            are resuming from previous incomplete runs.
            To reuse the code from ``setup``, simply set this to
            ``"setup"``, which calls the code inside the ``setup``
            function.
            """
        ),
    },
    {
        "args": ["--teardown"],
        "type": str,
        "help": format_help(
            """
            Bash code executed in "teardown" stage.
            """
        ),
    },
    {
        "args": ["--sbatch_options"],
        "type": json.loads,
        "help": format_help(
            """
            Dictionary of options to pass to sbatch.
            """
        ),
    },
    {
        "args": ["--cleanup_seconds"],
        "type": int,
        "help": format_help(
            """
            Interrupts a job n seconds before timeout to run cleanup
            tasks (teardown, auto-schedule new job).
            Default is 120 seconds.
            """
        ),
    },
    {
        "args": ["--submit"],
        "type": bool,
        "help": format_help(
            """
            Submit created job to scheduler. Set this to ``False`` if
            you are manually submitting the created ``$JOB_DIR`` later.
            Default is ``True``.
            """
        ),
    },
    {
        "args": ["--interactive"],
        "type": bool,
        "help": format_help(
            """
            Run as a blocking interactive job. Default is ``False``.
            """
        ),
    },
    {
        "args": ["--resubmit_limit"],
        "type": int,
        "help": format_help(
            """
            Maximum number of times to auto-submit a job for "resume".
            (Not entirely unlike submitting a resume for a job.)
            Default is 64 resubmissions.
            """
        ),
    },
    {
        "args": ["--config"],
        "type": str,
        "help": format_help(
            """
            Path to config file for formatting.
            """
        ),
    },
]


JOB_CONFIG_KEYS = [
    "job_dir",
    "src",
    "on_run",
    "on_run_resume",
    "setup",
    "setup_resume",
    "teardown",
    "sbatch_options",
    "cleanup_seconds",
    "submit",
    "interactive",
    "resubmit_limit",
    "config",
]


def parse_args(argv=None):
    # Add hyphenated version of options.
    for argument in ARGUMENTS:
        h_args = [x.replace("_", "-") for x in argument["args"]]
        argument["args"].extend(x for x in h_args if x not in argument["args"])

    parser = argparse.ArgumentParser()

    for argument in ARGUMENTS:
        parser.add_argument(
            *argument["args"],
            **{k: v for k, v in argument.items() if k != "args"},
        )

    args = parser.parse_args(argv)

    return args


def load_job_config(args):
    # Load from CLI.
    job_config = {k: v for k, v in vars(args).items() if v is not None}

    # Load from file.
    if args.job:
        with open(args.job) as f:
            job_config.update(yaml.safe_load(f))

    # Extra config for formatting purposes.
    if args.config:
        with open(args.config) as f:
            job_config["config"] = yaml.safe_load(f)

    # Discard unexpected keys.
    for k in job_config:
        if k not in JOB_CONFIG_KEYS:
            del job_config[k]

    return job_config


def main(argv=None):
    args = parse_args(argv)
    job_config = load_job_config(args)
    submit_job(**job_config)


if __name__ == "__main__":
    main()
