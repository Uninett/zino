=============================================
How to: Upgrade from Zino 1 (legacy/Tcl Zino)
=============================================

Zino 1 stores its running state to disk as a piece of Tcl code (usually
in ``save-state.tcl``). Zino 2 stores its running state in a JSON
formatted file (usually in ``zino-state.json``). These two files are not
compatible. In order to assist in converting a running Zino 1 system
into a Zino 2 system, we have provided the ``zinoconv`` program, which
attempts to read ``save-state.tcl`` and convert it into a valid
``zino-state.json``.

This converter is not yet fully tested in all situations, and may have
bugs. Also, Zino 1 has had bugs, and for a long-running Zino 1 system,
the ``save-state.tcl`` file may contain bits of outdated, useless or
incorrectly formatted data (incorrectly formatted IPv6 addresses is one
of these known issues). The ``zinoconv`` program may output lots of
warnings about broken Zino 1 data it will ignore.

To convert a ``save-state.tcl`` to ``zino-state.json``, you can use the
command like so:

.. code:: shell

   zinoconv save-state.tcl zino-state.json
