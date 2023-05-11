# Zino 2
[![build badge](https://img.shields.io/github/actions/workflow/status/Uninett/zino/tests.yml?branch=master)](https://github.com/Uninett/zino/actions)
[![codecov badge](https://codecov.io/gh/Uninett/zino/branch/master/graph/badge.svg)](https://codecov.io/gh/Uninett/zino)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

This is the modern Python re-implementation of the battle-proven Zino network
monitor, first implemented in Tcl/Scotty at Uninett in the 1990s.

This is still a work in progress, and is not yet a fully functional
replacement for the Tcl-based Zino.

Development of Zino 2.0 is fully sponsored by [NORDUnet](https://nordu.net/),
on behalf of the nordic NRENs.

## Running tests

[tox](https://tox.wiki/) and [pytest](https://pytest.org/) are used to run the
test suite. To run the test suite on all supported versions of Python, run:

```shell
tox
```

## Code style

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
