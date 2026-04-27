==========================================
How to: Check a Zino daemon with ``zping``
==========================================

``zping`` is a small command-line utility that asks a running Zino 2
daemon for its uptime via SNMP. It is intended as a quick, manual
liveness check from the shell.

Basic usage
===========

Query a Zino agent on the default address (``127.0.0.1:8000``)::

    $ zping
    Zino is alive (uptime: 2 days, 3 hours, 17 minutes)

Specify a host and port::

    $ zping zino.example.org 8000

Useful options:

``--community``
    SNMP v2c community string (default: ``public``).

``--timeout``
    Timeout in seconds for the SNMP request (default: ``5``).

Exit codes: ``0`` on a valid response (printed to stdout), ``1`` on any
failure (diagnostic written to stderr).
