=================================
Controlling Zino with daemontools
=================================

`daemontools <https://cr.yp.to/daemontools.html>`_ is a small collection of
tools for supervising long-running services.  It starts Zino at boot time,
restarts it if it crashes, and feeds its output into a set of automatically
rotated log files.  It is a good fit for systems that do not use *systemd*,
such as NetBSD and the other BSDs.

This assumes:

1. you have created a user ``zino``
2. the user ``zino`` has the home directory of ``/home/zino``
3. ``zino`` is installed in a virtualenv ``/home/zino/.zino``
4. Zino receives SNMP traps through a trap multiplexer, such as *straps*, which
   Zino starts by itself (see :ref:`configuring-trap-reception`)


Installing daemontools
======================

On NetBSD, the ``daemontools-run`` package from pkgsrc installs daemontools
along with an rc.d script that starts the supervisor, :program:`svscan`, at
boot time:

.. code-block:: sh

    pkgin install daemontools-run
    cp /usr/pkg/share/examples/rc.d/svscan /etc/rc.d/
    echo 'svscan=YES' >> /etc/rc.conf
    /etc/rc.d/svscan start

The package also creates the directory ``/var/service``, along with a
``/service`` symlink to it.  :program:`svscan` supervises every service found
in this directory.

On other systems, install daemontools from the system's package manager, and
make sure :program:`svscan` is started at boot time.  The location of its
service directory may differ from ``/service``.


Creating the service directory
==============================

A daemontools service is a directory containing an executable ``run`` script,
which starts the service in the foreground.  An optional ``log`` subdirectory
holds a second ``run`` script, which receives all the output of the first.

The scripts are run as root, so the service directory should be owned by
root and not be writable by the ``zino`` user.  Create it outside ``/service``
first, so that :program:`svscan` never picks up a half-finished service:

.. code-block:: sh

    mkdir -p /etc/sv/zino/log

Copy the :download:`zino-daemontools-run.example` file, reproduced below, to
``/etc/sv/zino/run``:

.. literalinclude:: zino-daemontools-run.example
   :language: sh

Copy the :download:`zino-daemontools-log-run.example` file, reproduced below,
to ``/etc/sv/zino/log/run``:

.. literalinclude:: zino-daemontools-log-run.example
   :language: sh

Make both scripts executable, and create the log directory:

.. code-block:: sh

    chmod +x /etc/sv/zino/run /etc/sv/zino/log/run
    mkdir -p /var/log/zino
    chown zino /var/log/zino

Finally, start Zino by linking the service directory into ``/service``.
:program:`svscan` will notice and start it within five seconds:

.. code-block:: sh

    ln -s /etc/sv/zino /service/


Setting environment variables
-----------------------------

On NetBSD, :program:`svscan` starts services with an empty environment, except
for ``PATH``, and :program:`setuidgid` does not set ``HOME``.  Environment
variables that Zino would otherwise inherit from a login shell or a boot
script must be set in the ``run`` script, before Zino is started.  For
example, Net-SNMP needs ``HOME`` to find the ``zino`` user's own configuration
files in ``~/.snmp``:

.. code-block:: sh

    export HOME=/home/zino


Running without root privileges
-------------------------------

The ``run`` script uses :program:`setuidgid` to switch to the ``zino`` user
*before* Zino itself is started.  The trap multiplexer is normally installed
setuid root, which lets it bind to the privileged SNMP trap port even when
started by an unprivileged Zino.  Zino therefore never needs root privileges,
and you need not set ``user`` in the ``[process]`` section of ``zino.toml``
(see :ref:`configuring-process`).

Note that :program:`setuidgid` only sets the user's primary group.  If the
``zino`` user depends on membership of supplementary groups to access files,
this access will be lost.

If Zino must bind to the SNMP trap port itself, or needs supplementary
groups, it must start as root.  In that case, remove :program:`setuidgid` from
the ``run`` script, and let Zino drop its privileges by setting ``user`` in
the ``[process]`` section of ``zino.toml``.  Unlike :program:`setuidgid`, Zino
keeps the user's supplementary groups.


Controlling Zino
================

Zino is controlled using the :program:`svc` and :program:`svstat` programs:

.. code-block:: sh

    svstat /service/zino     # Show whether Zino is running, and for how long
    svc -d /service/zino     # Stop Zino
    svc -u /service/zino     # Start Zino again
    svc -t /service/zino     # Restart Zino

Stopping and restarting both send ``SIGTERM`` to Zino, which will save its
state before exiting.

To stop Zino from being started at boot time, create a file named ``down`` in
the service directory.

To remove the service entirely, first remove the symlink, then stop both Zino
and its logger:

.. code-block:: sh

    rm /service/zino
    svc -dx /etc/sv/zino /etc/sv/zino/log


Stopping Zino at system shutdown
--------------------------------

At system shutdown, Zino receives ``SIGTERM`` along with every other process,
and is killed outright if it has not exited within a few seconds.  If Zino
needs longer than that to save a large state, the state will not be saved.
Since :program:`multilog` receives ``SIGTERM`` at the same time, Zino's final
log messages may be lost as well.

On NetBSD, you can make :program:`shutdown` stop Zino properly before this
happens, by adding these lines to ``/etc/rc.shutdown.final``:

.. code-block:: sh

    /usr/pkg/bin/svc -d /service/zino
    while /usr/pkg/bin/svstat /service/zino | grep -q ': up'; do
        sleep 1
    done

Note that this only takes effect when the system is brought down by
:program:`shutdown`, since :program:`reboot` and :program:`halt` skip the
shutdown scripts.  If ``rcshutdown_timeout`` is set in ``/etc/rc.conf``, it
also limits how long Zino is given to save its state.


Reading the logs
================

:program:`multilog` writes Zino's log output to ``/var/log/zino/current``.
When this file reaches 10 MiB (the ``s10485760`` argument), it is renamed to
a file whose name starts with ``@``, followed by a timestamp in the *TAI64N*
format.  The oldest of these files is removed whenever there are more than 19
of them (the ``n20`` argument counts ``current`` as well).  To follow the logs
continuously, run:

.. code-block:: sh

    tail -F /var/log/zino/current

:program:`multilog` can add its own timestamps to each line (the ``t``
argument), but these are also in the *TAI64N* format, which must be converted
by :program:`tai64nlocal` to be human-readable.  The example omits this, since
Zino's default log format already includes timestamps.  See
:ref:`configuring-logging` for more details on controlling Zino log output.


Troubleshooting
===============

If :program:`svstat` keeps reporting that Zino has been up for only a second
or two, Zino is crashing and being restarted over and over.  Zino's own log
should tell you why.

If the ``run`` script itself cannot be started, the error message will not
appear in Zino's log.  On NetBSD, :program:`svscan` sends these messages to
*syslog*, tagged ``nbsvscan``.


Using runit or s6 instead
=========================

`runit <https://smarden.org/runit/>`_ and `s6 <https://skarnet.org/software/s6/>`_
are both based on the design of daemontools.  The scripts above are easily
adapted to either of them, using their counterparts to :program:`setuidgid`
and :program:`multilog`.  Consult their documentation for details.
