=============================
Controlling Zino with systemd
=============================

This assumes:

1. you have created a user ``zino``
2. the user ``zino`` has the home directory of ``/home/zino``
3. ``zino`` is installed in a virtualenv ``/home/zino/.zino``

Copy the :download:`zino.service.example`_ file, reproduced below, to ``/etc/systemd/system/zino.service``.

.. literalinclude:: zino.service.example

This will start ``zino`` as root; ``zino`` will drop its root privileges by
itself as soon as port 162 is open for listening.
