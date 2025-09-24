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
while it’s running, so any changes made while Zino is running should be
picked up without requiring a restart of the process.

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
