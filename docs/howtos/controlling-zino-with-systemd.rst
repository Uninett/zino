=============================
Controlling Zino with systemd
=============================

This assumes:

1. you have created a user ``zino``
2. the user ``zino`` has the home directory of ``/home/zino``
3. ``zino`` is installed in a virtualenv ``/home/zino/.zino``

Copy the :download:`zino.service.example` file, reproduced below, to ``/etc/systemd/system/zino.service``.

.. literalinclude:: zino.service.example

To make systemd aware of the new unit, you should run:

.. code-block:: sh

    sudo systemctl daemon-reload

To enable the new unit to start automatically at system boot, run:

.. code-block:: sh

    sudo systemctl enable zino

To start Zino in the background now, run:

.. code-block:: sh

    sudo systemctl start zino

This will start ``zino`` as root; ``zino`` will drop its root privileges by
itself as soon as port 162 is open for listening.


Removing redundant timestamps in logs
=====================================

When running under *systemd*, Zino's log output is handled by *systemd* and is
viewable through the :program:`journalctl` program (e.g. `journalctl -u zino
-f` to follow the logs continuously).

However, *systemd* will add its own timestamps to log lines it receives, while
Zino's default log format includes timestamps. It might therefore be desirable
to change Zino's log format when running under *systemd*.  The default looks
something like this:

.. code-block:: toml
   :caption: zino.toml

    [logging.formatters.standard]
    format = "%(asctime)s - %(levelname)s - %(name)s (%(threadName)s) - %(message)s"

Which could easily be changed to this:

.. code-block:: toml
   :caption: zino.toml

    [logging.formatters.standard]
    format = "%(levelname)s - %(name)s (%(threadName)s) - %(message)s"

See :ref:`configuring-logging` for more details on controlling Zino log output.
