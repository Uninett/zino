=================================
How to: Use the Zino Docker image
=================================

The repository includes a ``Dockerfile`` and a ``docker-compose.yml`` file for
building and running Zino as a Docker container.

Building the image
------------------

Build the image locally from the Zino source tree:

.. code:: shell

   docker compose build

This builds the image and tags it ``zino:latest``.

Running the container
---------------------

.. code:: shell

   docker compose up

This starts Zino using the settings in ``docker-compose.yml``.

Configuration files
-------------------

The compose file mounts the current directory (``./``) into ``/zino`` inside the
container, which is also Zino's working directory.  The current directory must
contain the configuration files Zino needs: :file:`zino.toml`,
:file:`polldevs.cf` and :file:`secrets`.

Why host networking is required
-------------------------------

Zino identifies an incoming SNMP trap by its **source IP address**: it looks up
the sending device by that address and ignores the trap if it doesn't match a
device Zino polls.

This has an important consequence under Docker.  With the default **bridge**
networking and published ports (``-p 162:162/udp``), Docker rewrites the source
address of incoming UDP packets to the bridge gateway (e.g. ``172.17.0.1``).
Zino then sees every trap as coming from the gateway, matches none of them to a
device, and silently drops them all — the tell-tale symptom is a Zino that polls
correctly but never reacts to traps.

The bundled ``docker-compose.yml`` therefore uses **host networking**
(``network_mode: host``): the container shares the host's network stack with no
NAT, so Zino sees the real trap source addresses.  Host networking also means
the container binds host ports directly, so there is no ``ports:`` section —
ports 162 (traps), 8000 (the uptime agent) and 8001/8002 (the APIs) are served
on the host as-is.

If host networking is not an option, receive traps through an SNMP trap
multiplexer such as **nmtrapd** running on the host, outside Docker: the
multiplexer binds port 162 and forwards traps — with their original source
address — to Zino.  Point Zino at it with the ``[snmp.trap]`` ``source`` setting
(see :ref:`configuring-trap-reception`).

Running as your own user
------------------------

Binding the privileged trap port 162 requires starting as root, so the container
starts as root and then drops privileges to the built-in unprivileged ``zino``
user — it never keeps running as root.  To instead drop to your own host user,
so the mounted configuration and the state files Zino writes stay owned by (and
writable by) you, set ``HOST_UID`` and ``HOST_GID`` when starting it:

.. code:: shell

   HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose up

The compose file passes these to Zino's ``--user`` option, which drops to that
numeric UID/GID once port 162 is bound.  Whichever user Zino drops to must be
able to write the mounted directory, where it keeps its state file.

Using a different trap port
---------------------------

Zino listens on port 162 by default.  To use another port, add ``--trap-port``
to the ``command`` in the compose file, keeping the ``--user`` part:

.. code:: yaml

   command: "--user ${HOST_UID:-0}:${HOST_GID:-0} --trap-port 1162"

Using the pre-built image
-------------------------

To use the pre-built image from the GitHub Container Registry instead of
building locally, comment out the ``build`` and ``image: zino:latest`` lines in
the compose file and uncomment:

.. code:: yaml

   image: ghcr.io/uninett/zino:latest
