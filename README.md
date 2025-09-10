# Zino 2
[![build badge](https://img.shields.io/github/actions/workflow/status/Uninett/zino/tests.yml?branch=master)](https://github.com/Uninett/zino/actions)
[![codecov badge](https://codecov.io/gh/Uninett/zino/branch/master/graph/badge.svg)](https://codecov.io/gh/Uninett/zino)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

This is the modern Python re-implementation of the battle-proven Zino network
state monitor, first implemented in Tcl/Scotty at Uninett in the 1990s.

An incomplete list of features that have yet to be ported from legacy Zino:

- No support for reading trap messages from a trap multiplexer like
  `straps`/`nmtrapd`.  This type of functionality may potentially be achieved
  by employing general packet multiplexers.  See issue
  [#362](https://github.com/Uninett/zino/issues/362) for more details.

Development of Zino 2.0 is fully sponsored by [NORDUnet](https://nordu.net/),
on behalf of the nordic NRENs.

## Table of contents

- [What is Zino?](#what-is-zino)
- [Installing](#installing-zino)
- [Configuring](#configuring-zino)
- [Contributing](#developing-zino)

## What is Zino?

Zino Is Not OpenView.

Zino is an SNMP network monitor that began its life at Uninett in the mid
1990s.  It was a homegrown system written in Tcl, specifically to monitor the
routers of the Norwegian national research network (NREN), a large backbone
network that connects the widely geographically dispersed higher education and
research institutions of Norway.  Uninett was also part of NORDUnet, the
collaboration that interconnects the NRENs of the Nordic countries, and Zino
is also utilized to monitor the NORDUnet backbone.

Here's a quote about its features from the `README` file of the original Tcl
codebase:

```
 o Trap-driven polling; receives and interprets traps.
 o Periodic status polling (by default low frequency).
 o A simplistic event handling system.
 o A simple SMTP-like client/server protocol.
 o A TK-based user interface.

all in a little under 5000 lines of Tcl.
```

This project aims to port all this to Python, except for the TK-based user
interface.  The Python implementation keeps backwards compatibility with the
"simple SMTP-like client/server protocol", so that the existing user interface
clients can be re-used (such as *Ritz* and *cuRitz*).  Additionally, a new web
user interface client is being developed at https://github.com/uninett/howitz .

Zino is essentially a small program that can run in the background, monitoring
your router network for:

- Link state
- BGP session state
- BFD session state
- Juniper chassis alarms

All changes will result in an "event" (aka a "case"), in which Zino will log
all further related changes until the case is manually closed by a human
operator via the server protocol on port 8001 (essentially through some user
interface).

Notifications are typically achieved by having a client program to fetch active
events from the Zino server and decide from that which notifications need to be
sent.

Zino has very few dependencies, other than the Python packages required to run
it.  Zino serializes its running state to a JSON file on disk, and can resume
its work from this file when restarted.

Redundancy can thus be achieved by running two or more Zino servers in
parallel.  A typical solution is for one server to be the "master", and the
other to be a "hot standby".  To ensure the master and the standby are mostly
in sync, a typical solution is to transfer the state dump from the master to
the standby every 24 hours and then restarting the standby from the master's
state dump.  Zino clients can be typically be configured to automatically
switch to using a standby server if the master is unavailable.

## Installing Zino

First, ensure you have a Python version between 3.9 and 3.12 available on your
system. Second, we recommend creating a *Python virtual environment*, which is
isolated from other Python software installed on your system, and installing
Zino into that.

Zino also currently supports two separate SNMP back-end libraries:

- [PySNMP](https://pypi.org/project/pysnmplib/), a pure Python SNMP
  implementation, which should run right out-of-the-box (unfortunately, with
  poor performance).
- [netsnmp-cffi](https://pypi.org/project/netsnmp-cffi/), a Python binding to
  the stable and performant [Net-SNMP C library](https://www.net-snmp.org/).

### Running Zino with the PySNMP library

The current version of Zino selects the Net-SNMP backend by default.  If you do
not care about performance, are having a problem with the `netsnmp-cffi`
implementation, or just do not want to deal with the hassle of adding another C
library to you system, you can select the PySNMP back-end by changing the
appropriate setting in `zino.toml`.  Please see the section "Configuring Zino"
for more details.

### Running Zino with the Net-SNMP library

If you want to run Zino with the more performant C library, you need to first
ensure this library (at least version 5.9) is installed on your system.
E.g. on Debian, this would be provided by the
[libsnmp40](https://packages.debian.org/bookworm/libsnmp40) package.

If your're on Linux, the `netsnmp-cffi` Python package should already have a
version of this library bundled for most common versions of Linux and Python,
and you might not have to do anything.  If that is not the case, you may have
to build the `netsnmp-cffi` C shim from source, in which case you will also
need the Net-SNMP C header files and a C compiler toolchain.

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
```

Even if the Python virtual environment hasn't been activated in your shell, you
can still run Zino directly from inside this environment, like so:

```shell
./zino-env/bin/zino --help
```

By default, Zino will listen for incoming SNMP traps on UDP port `162`.  This
port is privileged (less than 1024), however, which means that Zino *needs to
be started as `root`* if you want to receive traps.  In order to avoid running
continuously with `root` privileges, the `--user` option can be used to tell
Zino to switch to running as a less privileged user as soon as port `162` has
been acquired.

Alternately, you can tell Zino to listen for traps on a non-privileged port,
e.g. by adding `--trap-port 1162` to the command line arguments, but this only
works if you can configure your SNMP agents to send traps to this non-standard
port.  In any case, you can also tell Zino to skip listening for traps by
specifying `--trap-port 0`.

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

### Configuring other settings

Other settings can be also configured in a separate [TOML](https://toml.io/en/) file,
which defaults to `zino.toml` in the current working directory, but a different file
can be specified using the `--config-file` command line option.

See the [zino.toml.example](./zino.toml.example) file for the settings that can be
configured and their default values.

Zino does not currently check `zino.toml` for changes on a scheduled interval while
it's running, so Zino needs to be restarted for changes to take effect.

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

## Upgrading from Zino 1 (legacy/Tcl Zino)

Zino 1 stores its running state to disk as a piece of Tcl code (usually in
`save-state.tcl`).  Zino 2 stores its running state in a JSON formatted file
(usually in `zino-state.json`).  These two files are not compatible.  In order
to assist in converting a running Zino 1 system into a Zino 2 system, we have
provided the `zinoconv` program, which attempts to read `save-state.tcl` and
convert it into a valid `zino-state.json`.

This converter is not yet fully tested in all situations, and may have bugs.
Also, Zino 1 has had bugs, and for a long-running Zino 1 system, the
`save-state.tcl` file may contain bits of outdated, useless or incorrectly
formatted data (incorrectly formatted IPv6 addresses is one of these known
issues).  The `zinoconv` program may output lots of warnings about broken Zino
1 data it will ignore.

To convert a `save-state.tcl` to `zino-state.json`, you can use the command
like so:

```shell
zinoconv save-state.tcl zino-state.json
```


## Developing Zino

### Development tools

A bunch of tools needed or recommended to have available when developing Zino
and/or running its test suite are listed in the requirements file
[requirements/dev.txt](./requirements/dev.txt).  These can be installed to your
development virtualenv using `pip` (or `uv pip`):

```sh
pip install -r requirements/dev.txt
```

### Running tests

[tox](https://tox.wiki/) and [pytest](https://pytest.org/) are used to run the
test suite. To run the test suite on all supported versions of Python, run:

```shell
tox run
```

### Code style

Zino code should follow the [PEP-8](https://peps.python.org/pep-0008/) and
[PEP-257](https://peps.python.org/pep-0257/)
guidelines. [Ruff](https://docs.astral.sh/ruff) is used for automatic code
formatting and linting. The [pre-commit](https://pre-commit.com/) tool is used
to enforce code styles at commit-time.

Before you start hacking, enable pre-commit hooks in your cloned repository,
like so:

```shell
pre-commit install
```


### Test trap examples

Running Zino during development might look like this (listening for traps on
the non-privileged port 1162):

```shell
zino --trap-port 1162
```

To send an example trap (`BGP4-MIB::bgpBackwardTransition`, which Zino ignores
by default), you can use a command like:

```shell
snmptrap -v2c -c public \
    127.0.0.1:1162 \
    '' \
    BGP4-MIB::bgpBackwardTransition \
    BGP4-MIB::bgpPeerRemoteAddr a 192.168.42.42 \
    BGP4-MIB::bgpPeerLastError x 4242 \
    BGP4-MIB::bgpPeerState i 2
```

### Using towncrier to automatically produce the changelog
#### Before merging a pull request
To be able to automatically produce the changelog for a release one file for each
pull request (also called news fragment) needs to be added to the folder
`changelog.d/`.

The name of the file consists of three parts separated by a period:
1. The identifier: the issue number
or the pull request number. If we don't want to add a link to the resulting changelog
entry then a `+` followed by a unique short description.
2. The type of the change: we use `security`, `removed`, `deprecated`, `added`,
`changed` and `fixed`.
3. The file suffix, e.g. `.md`, towncrier does not care which suffix a fragment has.

So an example for a file name related to an issue/pull request would be `214.added.md`
or for a file without corresponding issue `+fixed-pagination-bug.fixed.md`.

This file can either be created manually with a file name as specified above and the
changelog text as content or one can use towncrier to create such a file as following:

```console
$ towncrier create -c "Changelog content" 214.added.md
```

When opening a pull request there will be a check to make sure that a news fragment is
added and it will fail if it is missing.

#### Before a release
To add all content from the `changelog.d/` folder to the changelog file simply run
```console
$ towncrier build --version {version}
```
This will also delete all files in `changelog.d/`.

To preview what the addition to the changelog file would look like add the flag
`--draft`. This will not delete any files or change `CHANGELOG.md`. It will only output
the preview in the terminal.

A few other helpful flags:
- `date DATE` - set the date of the release, default is today
- `keep` - do not delete the files in `changelog.d/`

More information about [towncrier](https://towncrier.readthedocs.io).

### Making git blame ignore formatting changes
The Zino codebase has been slightly reformatted a couple of times. To make
`git blame` ignore these changes you can run
```console
$ git config blame.ignoreRevsFile .git-blame-ignore-revs
```
For more information check the
[git blame docs](https://git-scm.com/docs/git-blame#Documentation/git-blame.txt---ignore-revs-fileltfilegt).
