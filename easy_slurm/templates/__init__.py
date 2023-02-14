import os as _os


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


_dir_path = _os.path.dirname(_os.path.realpath(__file__))

with open(_os.path.join(_dir_path, "job.sh")) as _f:
    JOB_SCRIPT_TEMPLATE = _f.read()

JOB_SCRIPT_TEMPLATE = _format_template(JOB_SCRIPT_TEMPLATE)

with open(_os.path.join(_dir_path, "job_interactive.sh")) as _f:
    JOB_INTERACTIVE_TEMPLATE = _f.read()

JOB_INTERACTIVE_TEMPLATE = _format_template(JOB_INTERACTIVE_TEMPLATE)

VARS_TEMPLATE = r"""
EASY_SLURM_VERSION={easy_slurm_version}
JOB_DIR={job_dir}
RESUBMIT_LIMIT={resubmit_limit}
"""

VARS_TEMPLATE = VARS_TEMPLATE.strip("\n")
