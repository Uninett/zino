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

This starts Zino directly as the unprivileged ``zino`` user.  Zino still needs
to bind the SNMP trap port (UDP 162), and ports below 1024 normally require
root.  Rather than starting as root, the unit grants Zino the single Linux
capability that permits binding a privileged port — ``CAP_NET_BIND_SERVICE`` —
through the ``AmbientCapabilities`` directive, while ``CapabilityBoundingSet``
restricts the service to that one capability.  This way Zino can listen on port
162 without ever running with root privileges.

If you would rather have Zino start as root and drop its privileges afterwards
(for example on a system without ``AmbientCapabilities`` support), set ``user``
in the ``[process]`` section of ``zino.toml`` (see :ref:`configuring-process`)
and change the unit to run as ``User=root`` instead.


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
