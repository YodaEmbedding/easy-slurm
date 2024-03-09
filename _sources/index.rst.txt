Easy Slurm
==========

.. image:: https://img.shields.io/github/license/YodaEmbedding/easy-slurm?color=blue
   :target: https://github.com/YodaEmbedding/easy-slurm/blob/master/LICENSE

Easy Slurm allows you to easily manage and submit robust jobs to Slurm using Python and Bash.


Features
--------

- **Freezes** source code by copying to separate ``$JOB_DIR``.
- **Auto-submits** another job if current job times out.
- **Exposes hooks** for custom bash code: ``setup``/``setup_resume``, ``on_run``/``on_run_resume``, and ``teardown``.
- |Format job names|_ using parameters from config files.
- **Interactive** jobs supported for easy debugging.

.. _Format job names: #formatting
.. |Format job names| replace:: **Format job names**
.. .. _Interactive: #interactive-jobs


Installation
------------

.. code-block:: bash

    pip install easy-slurm


Usage
-----

To submit a job, simply fill in the various parameters shown in the example below.

.. code-block:: python

    import easy_slurm

    easy_slurm.submit_job(
        job_dir="$HOME/jobs/{date}-{job_name}",
        src=["./src", "./assets"],
        setup="""
            virtualenv "$SLURM_TMPDIR/env"
            source "$SLURM_TMPDIR/env/bin/activate"
            pip install -r "$SLURM_TMPDIR/src/requirements.txt"
        """,
        setup_resume="""
            # Runs only on subsequent runs. Call setup and do anything else needed.
            setup
        """,
        on_run="cd src && python main.py",
        on_run_resume="cd src && python main.py --resume",
        teardown="""
            # Do any cleanup tasks here.
        """,
        sbatch_options={
            "job-name": "example-simple",
            "account": "your-username",
            "time": "3:00:00",
            "nodes": "1",
        },
        resubmit_limit=64,  # Automatic resubmission limit.
    )

All job files will be kept in the ``job_dir`` directory. Provide directory paths to ``src`` -- these will be archived and copied to the ``job_dir`` directory. Also provide Bash code in the hooks, which will be run in the following order:

.. list-table:: Hooks order
   :widths: 50 50
   :header-rows: 1

   * - First run:
     - Subsequent runs:
   * - ``setup``
     - ``setup_resume``
   * - ``on_run``
     - ``on_run_resume``
   * - ``teardown``
     - ``teardown``

`Full examples`_ are available, including a `simple example`_ to run "training epochs" on a cluster.

.. _`Full examples`: https://github.com/YodaEmbedding/easy-slurm/tree/main/examples
.. _`simple example`: https://github.com/YodaEmbedding/easy-slurm/tree/main/examples/simple

YAML
~~~~

Jobs can also be fully configured using YAML files. See `examples/simple_yaml`_.

.. _`examples/simple_yaml`: https://github.com/YodaEmbedding/easy-slurm/tree/main/examples/simple_yaml

.. code-block:: yaml

    job_dir: "$HOME/jobs/{date}-{job_name}"
    src: ["./src", "./assets"]
    setup: |
      virtualenv "$SLURM_TMPDIR/env"
      source "$SLURM_TMPDIR/env/bin/activate"
      pip install -r "$SLURM_TMPDIR/src/requirements.txt"
    setup_resume: |
      # Runs only on subsequent runs. Call setup and do anything else needed.
      setup
    on_run: "cd src && python main.py"
    on_run_resume: "cd src && python main.py --resume"
    teardown: |
      # Do any cleanup tasks here.
    sbatch_options:
      job-name: "example-simple"
      account: "your-username"
      time: "3:00:00"
      nodes: 1
    resubmit_limit: 64  # Automatic resubmission limit.

Formatting
~~~~~~~~~~

One useful feature is formatting paths using custom template strings:

.. code-block:: python

    easy_slurm.submit_job(
        job_dir="$HOME/jobs/{date:%Y-%m-%d}-{job_name}",
    )

The job names can be formatted using a config dictionary:

.. code-block:: python

    job_name = easy_slurm.format.format_with_config(
        "bs={hp.batch_size:04},lr={hp.lr:.1e}",
        config={"hp": {"batch_size": 32, "lr": 1e-2}},
    )

    easy_slurm.submit_job(
        job_dir="$HOME/jobs/{date:%Y-%m-%d}-{job_name}",
        sbatch_options={
            "job-name": job_name,  # equals "bs=0032,lr=1.0e-02"
            ...
        },
        ...
    )

This helps in automatically creating descriptive, human-readable job names.


.. toctree::
	:hidden:

	Home <self>

.. toctree::
   :maxdepth: 1
   :caption: Guides
   :hidden:

   tutorials/installation
   tutorials/full

.. toctree::
   :maxdepth: 1
   :caption: Easy Slurm API
   :hidden:

   easy_slurm/jobs
   easy_slurm/format

.. toctree::
   :caption: Development
   :hidden:

   Github repository <https://github.com/YodaEmbedding/easy-slurm/>
