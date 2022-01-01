import os


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


_dir_path = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(_dir_path, "job.sh")) as _f:
    JOB_SCRIPT_TEMPLATE = _f.read()

JOB_SCRIPT_TEMPLATE = _format_template(JOB_SCRIPT_TEMPLATE)

VARS_TEMPLATE = r"""
JOB_DIR={job_dir}
DATASET_PATH={dataset_path}
"""

VARS_TEMPLATE = VARS_TEMPLATE.strip("\n")

JOB_INTERACTIVE_TEMPLATE = """
#!/bin/bash -v

source {job_path} --interactive
"""
