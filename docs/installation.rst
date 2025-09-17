Installing Zino
===============

First, ensure you have a Python version beyween 3.9 and 3.12 available on your
system. Second, we recommend creating a *Python virtual environment*, which is
isolated from other Python software installed on your system, and installing
Zino into that.

Zino also currently supports two separate SNMP back-end libraries:

-  `PySNMP <https://pypi.org/project/pysnmplib/>`_, a pure Python SNMP
   implementation, which should run right out-of-the-box (unfortunately,
   with poor performance).
-  `netsnmp-cffi <https://pypi.org/project/netsnmp-cffi/>`_, a Python
   binding to the stable and performant `Net-SNMP C
   library <https://www.net-snmp.org/>`_.

Running Zino with the PySNMP library
------------------------------------

The current version of Zino selects the Net-SNMP backend by default. If you do
not care about performance, are having a problem with the ``netsnmp-cffi``
implementation, or just do not want to deal with the hassle of adding another
C library to you system, you can select the PySNMP back-end by changing the
appropriate setting in ``zino.toml``. Please see the section :doc:`Configuring
Zino </configuration>` for more details.

Running Zino with the Net-SNMP library
--------------------------------------

If you want to run Zino with the more performant C library, you need to
first ensure this library (at least version 5.9) is installed on your
system. E.g. on Debian, this would be provided by the
`libsnmp40 <https://packages.debian.org/bookworm/libsnmp40>`_ package.

If you're on Linux, the ``netsnmp-cffi`` Python package should already
have a version of this library bundled for most common versions of Linux
and Python, and you might not have to do anything. If that is not the
case, you may have to build the ``netsnmp-cffi`` C shim from source, in
which case you will also need the Net-SNMP C header files and a C
compiler toolchain.

Creating a Python virtual environment for Zino
----------------------------------------------

To create a new virtual environment in the directory ``./zino-env``,
run:

.. code:: shell

   python -m venv ./zino-env

This virtual environment can now be *activated* in your shell, so that
any further Python related commands that are run in your shell are
running from inside the new environment:

.. code:: shell

   . ./zino-env/bin/activate

Installing from PyPI
--------------------

With your Zino virtual environment activated in your shell, run:

.. code:: shell

   pip install zino

Installing from source
----------------------

With your Zino virtual environment activated in your shell, clone the
Zino source code directly from GitHub and install it from there:

.. code:: shell

   git clone https://github.com/Uninett/zino.git
   cd zino
   pip install .

Running Zino for the first time
-------------------------------

In order for Zino to function properly, you first need to make a minimal
``polldevs.cf`` configuration file, as described in the next section.
However, at this point you can test that the ``zino`` command is
available to run:

.. code:: console

   $ zino --help
   usage: zino [-h] [--polldevs PATH] [--debug] [--stop-in N] [--trap-port PORT] [--user USER]

   Zino is not OpenView

   options:
     -h, --help        show this help message and exit
     --polldevs PATH   Path to polldevs.cf
     --debug           Set global log level to DEBUG. Very chatty!
     --stop-in N       Stop zino after N seconds.
     --trap-port PORT  Which UDP port to listen for traps on. Default value is 162. Any value below 1024 requires root privileges. Setting to 0
                       disables SNMP trap monitoring.
     --user USER       Switch to this user immediately after binding to privileged ports

Even if the Python virtual environment hasn't been activated in your
shell, you can still run Zino directly from inside this environment,
like so:

.. code:: shell

   ./zino-env/bin/zino --help

By default, Zino will listen for incoming SNMP traps on UDP port
``162``. This port is privileged (less than 1024), however, which means
that Zino *needs to be started as ``root``* if you want to receive
traps. In order to avoid running continuously with ``root`` privileges,
the ``--user`` option can be used to tell Zino to switch to running as a
less privileged user as soon as port ``162`` has been acquired.

Alternately, you can tell Zino to listen for traps on a non-privileged
port, e.g. by adding ``--trap-port 1162`` to the command line arguments,
but this only works if you can configure your SNMP agents to send traps
to this non-standard port. In any case, you can also tell Zino to skip
listening for traps by specifying ``--trap-port 0``.


Running Zino in production
--------------------------

In order to run Zino in a production setting, you should set up some service
orchestration of the process.  I.e. the process should run in the background,
its log output should be directed to somewhere it will be persisted, and the
process should automatically be started at boot time and restarted if it
crashes during runtime.

If you're on a system that uses *systemd* for service management, please read
:doc:`/howtos/controlling-zino-with-systemd`
