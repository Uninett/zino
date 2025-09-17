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
