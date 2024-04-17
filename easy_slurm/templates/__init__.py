import os as _os

_dir_path = _os.path.dirname(_os.path.realpath(__file__))


def _read_template(filename: str, dir_path: str = _dir_path) -> str:
    with open(_os.path.join(dir_path, filename)) as f:
        return _format_template(f.read())


def _format_template(s: str) -> str:
    return (
        s.strip("\n")
        .replace("{{", "<LBRACE>")
        .replace("}}", "<RBRACE>")
        .replace("{", "{{")
        .replace("}", "}}")
        .replace("<LBRACE>", "{")
        .replace("<RBRACE>", "}")
    )


JOB_SCRIPT_TEMPLATE = _read_template("job.sh")

JOB_INTERACTIVE_TEMPLATE = _read_template("job_interactive.sh")

VARS_TEMPLATE = r"""
EASY_SLURM_VERSION={easy_slurm_version}
JOB_DIR={job_dir}
RESUBMIT_LIMIT={resubmit_limit}
"""

VARS_TEMPLATE = VARS_TEMPLATE.strip("\n")
