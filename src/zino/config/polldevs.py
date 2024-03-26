"""Functionality to parse and validate the legacy polldevs.cf config file"""

from typing import Iterator, TextIO

from zino.config.models import PollDevice


def read_polldevs(filename: str) -> Iterator[PollDevice]:
    """Reads and parses the legacy `polldevs.cf` format, yielding a sequence of PollDevice objects.

    This parser is slightly more lax than the original Tcl-based parser, in that it allows multiple empty lines or
    multiple spaces in value assignments.
    """
    defaults = {}
    with open(filename, "r") as devs:
        for section in _read_conf_sections(devs):
            if _contains_defaults(section):
                defaults.update(_parse_defaults(section))
                continue

            yield PollDevice(**(defaults | section))


def _read_conf_sections(filehandle: TextIO) -> Iterator[dict]:
    """Reads individual configuration sections from `polldevs.cf`, yielding each one as a separate dict"""
    section = {}
    for line in filehandle:
        line = line.strip()
        if line.startswith("#"):
            continue
        if not line:
            if section:
                yield section
                section = {}
            continue
        try:
            key, value = line.split(":", maxsplit=1)
        except ValueError:
            raise InvalidConfiguration(f"{line!r} is not a valid configuration line")
        section[key.strip()] = value.strip()
    if section:
        yield section


def _contains_defaults(section: dict) -> bool:
    return any(key.startswith("default ") for key in section)


def _parse_defaults(section: dict) -> dict:
    return {key.split(" ", maxsplit=1)[1]: value for key, value in section.items() if key.startswith("default ")}


class InvalidConfiguration(Exception):
    pass
