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

with open(os.path.join(_dir_path, "job_interactive.sh")) as _f:
    JOB_INTERACTIVE_TEMPLATE = _f.read()

JOB_INTERACTIVE_TEMPLATE = _format_template(JOB_INTERACTIVE_TEMPLATE)

VARS_TEMPLATE = r"""
JOB_DIR={job_dir}
DATASET_PATH={dataset_path}
"""

VARS_TEMPLATE = VARS_TEMPLATE.strip("\n")

EXTRACT_RESULTS = {
    "rsync": r"""
        mkdir -p "$JOB_DIR/results"
        mkdir -p "$SLURM_TMPDIR/results"
        rsync -a "$JOB_DIR/results/" "$SLURM_TMPDIR/results/"
    """,
    "symlink": r"""
        mkdir -p "$JOB_DIR/results/"
        ln -s "$JOB_DIR/results" "$SLURM_TMPDIR/results"
    """,
    "targz": r"""
        if [ "$IS_FIRST_RUN" = false ]; then
          tar xf "$JOB_DIR/results.tar.gz"
        fi
        mkdir -p "$SLURM_TMPDIR/results"
    """,
}

EXTRACT_RESULTS = {k: v.strip("\n") for k, v in EXTRACT_RESULTS.items()}

SAVE_RESULTS = {
    "rsync": r"""
        rsync -a --partial "$SLURM_TMPDIR/results/" "$JOB_DIR/results/"
    """,
    "symlink": r"""
    """,
    "targz": r"""
        tar czf results.tar.gz results
        mv results.tar.gz "$JOB_DIR/"
    """,
}

SAVE_RESULTS = {k: v.strip("\n") for k, v in SAVE_RESULTS.items()}
