# Zino 2
[![build badge](https://img.shields.io/github/actions/workflow/status/Uninett/zino/tests.yml?branch=master)](https://github.com/Uninett/zino/actions)
[![codecov badge](https://codecov.io/gh/Uninett/zino/branch/master/graph/badge.svg)](https://codecov.io/gh/Uninett/zino)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![rtfd badge](https://app.readthedocs.org/projects/zino/badge/?version=latest&style=flat)](https://zino.readthedocs.io/en/latest/)
[![Python 3.9](https://img.shields.io/badge/python-3.9-blue.svg)](https://www.python.org/downloads/release/python-3922/)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-31018/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-31113/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-31211/)

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
- [Using](#using-zino)
- [Upgrade from Zino 1](docs/howtos/upgrade-from-zino-1.rst)
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
clients can be re-used (such as *Ritz* and *cuRitz*).

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

You need a supported Python version, and these days a virtualenv for
dependencies. You also need to choose one of two supported SNMP libraries, by
default it is backed by a C-library, Net-SNMP.

We recommend you create a user to own zino's files instead of
having everything be owned by root

See [Installation](docs/installation.rst) for the full details.

## Configuring Zino

Zino *must* have at minimum one configuration file: ``polldevs.cf``, which
keeps track of at least one SNMP-enabled router to monitor. See
[Configuring](docs/configuration.rst) for the details.

## Using Zino

This package only represents the Zino server backend. In order to meaningfully
interface with Zino as a user, you will want a remote interface to
Zino. Several remote interfaces exist.

* [curitz](https://github.com/Uninett/curitz) is a curses-based terminal
  application to interface with Zino. It is currently the best client for
  day-to-day use.

* *Ritz* is the original Remote Interface To Zino. It is an X11 desktop
  application written in Tcl/Tk. Unfortunately, the source code isn't currently
  available.

* [Howitz](https://github.com/Uninett/howitz) is a web-based remote interface
  to Zino that was originally written as part of the Zino 2.0 project. However,
  it has since been discontinued in favor of integration with
  [Argus](http://github.com/Uninett/Argus) using the
  [zino-argus glue service](https://github.com/Uninett/zino-argus-glue).


## Developing Zino

Contributions are welcome, at this point especially bug reports (patches
welcome), missing documentation, how to's and usage tips!

See [Developing Zino](docs/development.rst) for tips, expectations and
assumptions.
