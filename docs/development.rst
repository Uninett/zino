===============
Developing Zino
===============

Development tools
=================

A bunch of tools needed or recommended to have available when developing
Zino and/or running its test suite are included in dependency groups in the
``pyproject.toml`` file (`local: <../pyproject.toml>`_, `online:
<https://github.com/Uninett/zino/pyproject.toml>`_).

The groups are:

* ``test`` just for testing tools
* ``maintenance`` for packagong and release tools
* ``dev`` includes ``test`` and ``maintenance`` tools as weel as linters, formatters and other helpers.

Install all of them to your development virtualenv using ``pip`` (or ``uv pip``):

.. code:: shell

   pip install --group dev

Running tests
=============

`tox <https://tox.wiki/>`__ and `pytest <https://pytest.org/>`__ are
used to run the test suite. To run the test suite on all supported
versions of Python, run:

.. code:: shell

   tox run

In order to run all the tests you need the non-python program ``snmptrap``. On
debian-derived distros it is included in the ``snmp`` package, install it via:

.. code:: shell

   apt install snmp

If this package is not installed some tests will be skipped.


Code style
==========

Zino code should follow the
`PEP-8 <https://peps.python.org/pep-0008/>`__ and
`PEP-257 <https://peps.python.org/pep-0257/>`__ guidelines.
`Ruff <https://docs.astral.sh/ruff>`__ is used for automatic code
formatting and linting. The `pre-commit <https://pre-commit.com/>`__
tool is used to enforce code styles at commit-time.

Before you start hacking, enable pre-commit hooks in your cloned
repository, like so:

.. code:: shell

   pre-commit install

Test trap examples
==================

Running Zino during development might look like this (listening for
traps on the non-privileged port 1162):

.. code:: shell

   zino --trap-port 1162

To send an example trap (``BGP4-MIB::bgpBackwardTransition``, which Zino
ignores by default), you can use a command like:

.. code:: shell

   snmptrap -v2c -c public \
       127.0.0.1:1162 \
       '' \
       BGP4-MIB::bgpBackwardTransition \
       BGP4-MIB::bgpPeerRemoteAddr a 192.168.42.42 \
       BGP4-MIB::bgpPeerLastError x 4242 \
       BGP4-MIB::bgpPeerState i 2

Using towncrier to automatically produce the changelog
======================================================

Before merging a pull request
-----------------------------

To be able to automatically produce the changelog for a release one file
for each pull request (also called news fragment) needs to be added to
the folder ``changelog.d/``.

The name of the file consists of three parts separated by a period: 1.
The identifier: the issue number or the pull request number. If we don’t
want to add a link to the resulting changelog entry then a ``+``
followed by a unique short description. 2. The type of the change: we
use ``security``, ``removed``, ``deprecated``, ``added``, ``changed``
and ``fixed``. 3. The file suffix, e.g. ``.md``, towncrier does not care
which suffix a fragment has.

So an example for a file name related to an issue/pull request would be
``214.added.md`` or for a file without corresponding issue
``+fixed-pagination-bug.fixed.md``.

This file can either be created manually with a file name as specified
above and the changelog text as content or one can use towncrier to
create such a file as following:

.. code:: console

   $ towncrier create -c "Changelog content" 214.added.md

When opening a pull request there will be a check to make sure that a
news fragment is added and it will fail if it is missing.

Before a release
----------------

To add all content from the ``changelog.d/`` folder to the changelog
file simply run

.. code:: console

   $ towncrier build --version {version}

This will also delete all files in ``changelog.d/``.

To preview what the addition to the changelog file would look like add
the flag ``--draft``. This will not delete any files or change
``CHANGELOG.md``. It will only output the preview in the terminal.

A few other helpful flags: - ``date DATE`` - set the date of the
release, default is today - ``keep`` - do not delete the files in
``changelog.d/``

More information about `towncrier <https://towncrier.readthedocs.io>`__.

Making git blame ignore formatting changes
==========================================

The Zino codebase has been slightly reformatted a couple of times. To
make ``git blame`` ignore these changes you can run

.. code:: console

   $ git config blame.ignoreRevsFile .git-blame-ignore-revs

For more information check the `git blame
docs <https://git-scm.com/docs/git-blame#Documentation/git-blame.txt---ignore-revs-fileltfilegt>`__.
