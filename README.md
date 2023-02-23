# Zino 2

This is the modern Python re-implementation of the battle-proven Zino network
monitor, first implemented in Tcl/Scotty at Uninett in 1999.

## Running tests

[tox](https://tox.wiki/) and [pytest](https://pytest.org/) are used to run the
test suite. To run the test suite on all supported versions of Python, run:

```shell
tox
```

## Code style

Zino code should follow the [PEP-8](https://peps.python.org/pep-0008/) and
[PEP-257](https://peps.python.org/pep-0257/)
guidelines. [Black](https://github.com/psf/black) is used for automatic code
formatting. The [pre-commit](https://pre-commit.com/) tool is used to enforce
code styles at commit-time.

To enable pre-commit hooks in your cloned repository, run:

```shell
pre-commit install
```
