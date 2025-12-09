================
Configuring Zino
================

Minimal configuration
=====================

At minimum, Zino must be configured with a list of SNMP-enabled routers to
monitor, the :file:`polldevs.cf` file, and a list of users, the :file:`secrets`
file.

By default, it looks for :file:`polldevs.cf` in the current
working directory, but a different configuration file can be specified
using the ``--polldevs`` command line option.

See :download:`polldevs.cf.example <../polldevs.cf.example>` file for an
example of the configuration format, reproduced below:

.. literalinclude:: ../polldevs.cf.example

Zino will check :file:`polldevs.cf` for changes on a scheduled interval
while it's running, so any changes made while Zino is running should be
picked up without requiring a restart of the process.

polldevs.cf reference
---------------------

The following settings can be configured either as global defaults (prefixed with
``default``) or per-device overrides:

.. list-table:: polldevs.cf settings
   :widths: 20 15 65
   :header-rows: 1

   * - Setting
     - Default
     - Description
   * - ``community``
     - ``public``
     - SNMP community string
   * - ``snmpversion``
     - ``v2c``
     - SNMP version (``v1`` or ``v2c``)
   * - ``port``
     - ``161``
     - SNMP UDP port
   * - ``timeout``
     - ``5``
     - SNMP request timeout in seconds
   * - ``retries``
     - ``3``
     - Number of SNMP request retries
   * - ``interval``
     - ``5``
     - Polling interval in minutes
   * - ``priority``
     - ``100``
     - Scheduling priority (higher = more frequent)
   * - ``domain``
     - (none)
     - DNS domain suffix
   * - ``statistics``
     - ``yes``
     - Collect interface statistics
   * - ``do_bgp``
     - ``yes``
     - Monitor BGP sessions
   * - ``ignorepat``
     - (none)
     - Regex pattern for interfaces to ignore
   * - ``watchpat``
     - (none)
     - Regex pattern for interfaces to monitor (if set, only matching interfaces are monitored)
   * - ``max-repetitions``
     - (backend-specific)
     - Maximum number of variable bindings returned per SNMP GET-BULK request.
       Lower values reduce load on SNMP agents but may increase the number of
       requests needed to complete walk operations. Useful for devices with slow
       SNMP agents that may timeout with higher values. If not set, each SNMP
       method uses its own default (typically 5 for netsnmp, 10 for pysnmp).

Example with ``max-repetitions``:

.. code-block:: none

   # Global default: use lower max-repetitions for all devices
   default max-repetitions: 5

   # Device with an especially slow SNMP agent
   name: slow-router
   address: 192.168.1.1
   max-repetitions: 3

The :file:`secrets` file is of a much simpler format, see
:ref:`configuring-api-users`. If it is readable for other users than the one
Zino runs as, Zino will log a warning. This file is read on every log in.

Configuring other settings
==========================

Other settings can be also configured in a separate
`TOML <https://toml.io/en/>`__ file, which defaults to ``zino.toml`` in
the current working directory, but a different file can be specified
using the ``--config-file`` command line option.

See the :download:`zino.toml.example <../zino.toml.example>` file for the
settings that can be configured and their default values, reproduced below:

.. literalinclude:: ../zino.toml.example

Zino does not currently check ``zino.toml`` for changes on a scheduled
interval while it’s running, so Zino needs to be restarted for changes
to take effect.

.. _configuring-logging:

Configuring logging
-------------------

Zino uses the logging framework provided by the Python standard library. Most
aspects of how Zino handles logging can also be controlled through
:file:`zino.toml`. Specifically, Zino automatically feeds everything under the
`logging` section of :file:`zino.toml` to Python's
:py:func:`logging.config.dictConfig`. For a complete overview of which options
exist, please refer to `Python's documentation of the configuration dictionary
schema
<https://docs.python.org/3/library/logging.config.html#logging-config-dictschema>`_.
The Zino example config includes comments that show Zino's default logging
setup.

Zino's log output is organized into a hierarchy of loggers that correspond to
the internal Python module hierarchy of Zino, which means that the log level of
different parts of Zino can be controlled individually.  If, for example, you
specifically wanted the reachability task to log debug message, you could add
this to the configuration:

.. code-block:: toml
   :caption: zino.toml

    [logging.loggers."zino.tasks.reachabletask"]
    level = "DEBUG"

A more complex example could be to specifically output all kinds of debug-level
information from `netsnmp-cffi` and the Net-SNMP C library to *a separate
file*. Due to the sheer volume of debug logs, it could even be desirable to
enable automatic log rotation every time the log file exceeds 1GB in size:

.. code-block:: toml
   :caption: zino.toml

    # Separate file handler for netsnmpy debug logs
    [logging.handlers.netsnmp_file]
    class = "logging.handlers.RotatingFileHandler"
    formatter = "standard"
    filename = "netsnmp-debug.log"
    maxBytes = 1073741824  # 1GB
    # Keep 3 backup files
    backupCount = 3

    # Send netsnmpy debug logs to a separate file to avoid console spam
    [logging.loggers.netsnmpy]
    level = "DEBUG"
    handlers = ["netsnmp_file"]
    # Avoid duplicate log message by disabling propagation to the root logger
    propagate = false

.. tip::

   Zino can also be manually made to log its list of currently executing
   polling jobs (including their start times and runtime duration) by sending
   it the ``USR1`` signal to a running Zino process, for example by using a
   command like ``pkill -SIGUSR1 zino``.

.. _configuring-api-users:

Configuring API users
=====================

Zino 2 reimplements the text-based (vaguely SMTP-esque) API protocol
from Zino 1, warts and all. This means that the protocol runs over
**unencrypted** TCP sessions. Access to restricted API information
requires authentication through the ``USER`` command. Usernames and
passwords are configured in *cleartext* in a :file:`secrets` file, e.g.:

::

   user1 password123
   user2 my-pets-name

You should therefore ensure that the :file:`secrets` file is only readable
for the user that the ``zino`` command runs as.

Please note that passwords are *not transmitted in cleartext* over API
socket connections. The Zino server protocol utilizes a
challenge-response mechanism, in which the user logging in must prove
that they know the password by giving a correct response to the given
challenge.

When opening a connection to the API port, the Zino server will
immediately send a hello message with a session challenge included:

.. code:: console

   $ telnet localhost 8001
   Trying 127.0.0.1...
   Connected to localhost.
   Escape character is '^]'.
   200 6077fe9fa53e4921b35c11cf6ef8891bc0194875 Hello, there

To authenticate properly, the client must issue the ``USER`` command,
which has two arguments: A username and a challenge response string.
Given the challenge value from above
(``6077fe9fa53e4921b35c11cf6ef8891bc0194875``), the proper challenge
response for ``user1`` can be computed on the command line thus:

.. code:: shell

   $ echo -n "6077fe9fa53e4921b35c11cf6ef8891bc0194875 password123" | sha1sum
   4daf3c1448c2c4b3b92489024cc4676f70c26b1d  -
   $

The proper way to authenticate as ``user1`` would then be to issue this
command:

::

   USER user1 4daf3c1448c2c4b3b92489024cc4676f70c26b1d
