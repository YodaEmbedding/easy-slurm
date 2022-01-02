#!/bin/bash -v

{{sbatch_options_str}}

source {{job_path}} --interactive
