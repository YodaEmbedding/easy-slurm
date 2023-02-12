Installation
============

**Requirements:** Python 3.7+.

Using pip
---------

.. code-block:: bash

    pip install easy-slurm


Using poetry
------------

First, clone the repository:

.. code-block:: bash

    git clone "https://github.com/YodaEmbedding/easy-slurm.git" easy-slurm

Poetry helps manage version-pinned virtual environments. First, `install Poetry`_:

.. code-block:: bash

    curl -sSL https://install.python-poetry.org | python3 -

.. _install Poetry: https://python-poetry.org/docs/#installation

Then, create the virtual environment and install the required Python packages:

.. code-block:: bash

    cd easy-slurm

    # Install Python packages to new virtual environment.
    poetry install
    echo "Virtual environment created in $(poetry env list --full-path)"

To activate the virtual environment, run:

.. code-block:: bash

    poetry shell
