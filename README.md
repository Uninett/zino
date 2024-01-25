# Zino 2
[![build badge](https://img.shields.io/github/actions/workflow/status/Uninett/zino/tests.yml?branch=master)](https://github.com/Uninett/zino/actions)
[![codecov badge](https://codecov.io/gh/Uninett/zino/branch/master/graph/badge.svg)](https://codecov.io/gh/Uninett/zino)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

This is the modern Python re-implementation of the battle-proven Zino network
state monitor, first implemented in Tcl/Scotty at Uninett in the 1990s.

This is still a work in progress, and is not yet a fully functional replacement
for the original Tcl-based Zino.  An incomplete list of features that have yet
to be ported:

- SNMP trap reception
  - Hence, no port flapping status
- Planned maintenance (the `PM` family of API commands)
- Router and single-port poll triggering from the API (the `POLLRTR` and
  `POLLINTF` API commands)

Development of Zino 2.0 is fully sponsored by [NORDUnet](https://nordu.net/),
on behalf of the nordic NRENs.

## Installing Zino

First, ensure you have Python 3.9, 3.10 or 3.11 available on your system.
Second, we recommend creating a *Python virtual environment*, which is
isolated from other Python software installed on your system, and installing
Zino into that.

### Creating a Python virtual environment for Zino

To create a new virtual environment in the directory `./zino-env`, run:

```shell
python -m venv ./zino-env
```

This virtual environment can now be "activated" in your shell, so that any
further Python related commands that are run in your shell are running from inside the
new environment:

```shell
. ./zino-env/bin/activate
```

### Installing from PyPI

With your Zino virtual environment activated in your shell, run:

```shell
pip install zino
```

### Installing from source

With your Zino virtual environment activated in your shell, clone the Zino
source code directly from GitHub and install it from there:

```shell
git clone https://github.com/Uninett/zino.git
cd zino
pip install .
```

### Running Zino for the first time

In order for Zino to function properly, you first need to make a minimal
`polldevs.cf` configuration file, as described in the next section.  However,
at this point you can test that the `zino` command is available to run:

```console
$ zino --help
usage: zino [-h] [--polldevs PATH] [--debug] [--stop-in N]

Zino is not OpenView

options:
  -h, --help       show this help message and exit
  --polldevs PATH  Path to polldevs.cf
  --debug          Set global log level to DEBUG. Very chatty!
  --stop-in N      Stop zino after N seconds.
```

Even if the Python virtual environment hasn't been activated in your shell, you
can still run Zino directly from inside this environment, like so:

```shell
./zino-env/bin/zino --help
```

### Configuring Zino

### Minimal configuration

At minimum, Zino must be configured with a list of SNMP-enabled routers to
monitor.  By default, it looks for `polldevs.cf` in the current working
directory, but a different configuration file can be specified using the
`--polldevs` command line option.

See the [polldevs.cf.example](./polldevs.cf.example) file for an example of the
configuration format.

Zino will check `polldevs.cf` for changes on a scheduled interval while it's
running, so any changes made while Zino is running should be picked up without
requiring a restart of the process.

### Configuring API users

Zino 2 reimplements the text-based (vaguely SMTP-esque) API protocol from Zino
1, warts and all.  This means that the protocol runs over **unencrypted** TCP
sessions.  Access to restricted API information requires authentication through
the `USER` command.  Usernames and passwords are configured in *cleartext* in a
`secrets` file, e.g.:

```
user1 password123
user2 my-pets-name
```

You should therefore ensure that the `secrets` file is only readable for the
user that the `zino` command runs as.

Please note that passwords are *not transmitted in cleartext* over API socket
connections.  The Zino server protocol utilizes a challenge-response mechanism,
in which the user logging in must prove that they know the password by giving a
correct response to the given challenge.

When opening a connection to the API port, the Zino server will immediately
send a hello message with a session challenge included:

```console
$ telnet localhost 8001
Trying 127.0.0.1...
Connected to localhost.
Escape character is '^]'.
200 6077fe9fa53e4921b35c11cf6ef8891bc0194875 Hello, there
```

To authenticate properly, the client must issue the `USER` command, which has
two arguments: A username and a challenge response string.  Given the challenge
value from above (`6077fe9fa53e4921b35c11cf6ef8891bc0194875`), the proper
challenge response for `user1` can be computed on the command line thus:

```shell
$ echo -n "6077fe9fa53e4921b35c11cf6ef8891bc0194875 password123" | sha1sum
4daf3c1448c2c4b3b92489024cc4676f70c26b1d  -
$
```

The proper way to authenticate as `user1` would then be to issue this command:

```
USER user1 4daf3c1448c2c4b3b92489024cc4676f70c26b1d
```

## Developing Zino

### Running tests

[tox](https://tox.wiki/) and [pytest](https://pytest.org/) are used to run the
test suite. To run the test suite on all supported versions of Python, run:

```shell
tox
```

### Code style

Zino code should follow the [PEP-8](https://peps.python.org/pep-0008/) and
[PEP-257](https://peps.python.org/pep-0257/)
guidelines. [Black](https://github.com/psf/black) and
[isort](https://pycqa.github.io/isort/) are used for automatic code
formatting. The [pre-commit](https://pre-commit.com/) tool is used to enforce
code styles at commit-time.

Before you start hacking, enable pre-commit hooks in your cloned repository,
like so:

```shell
pre-commit install
```
