"""Functionality to parse and validate the legacy polldevs.cf config file"""

from typing import Iterator, TextIO, Tuple

from pydantic import ValidationError

from zino.config.models import PollDevice


def read_polldevs(filename: str) -> Iterator[PollDevice]:
    """Reads and parses the legacy `polldevs.cf` format, yielding a sequence of PollDevice objects.

    This parser is slightly more lax than the original Tcl-based parser, in that it allows multiple empty lines or
    multiple spaces in value assignments.
    """
    defaults = {}
    try:
        with open(filename, "r") as devs:
            for lineno, section in _read_conf_sections(devs):
                if _contains_defaults(section):
                    defaults.update(_parse_defaults(section))
                    continue

                try:
                    yield PollDevice(**(defaults | section))
                except ValidationError as error:
                    first_error = error.errors()[0]
                    device_name = section.get("name", "N/A")
                    attribute = first_error["loc"][0]
                    raise InvalidConfiguration(
                        f"Validation error in device block {device_name!r}: {first_error['msg']} ({attribute!r})",
                        filename=filename,
                        lineno=lineno,
                    )

    except InvalidConfiguration as error:
        error.filename = filename
        raise


def _read_conf_sections(filehandle: TextIO) -> Iterator[Tuple[int, dict]]:
    """Reads and yields individual configuration sections from `polldevs.cf`.

    Each yielded value is a two-tuple of the first line number of the section and the parsed section as a dict.
    """
    section = {}
    first_line = None
    for lineno, line in enumerate(filehandle):
        if not first_line:
            first_line = lineno + 1
        line = line.strip()
        if line.startswith("#"):
            continue
        if not line:
            if section:
                yield first_line, section
                section = {}
                first_line = None
            continue
        try:
            key, value = line.split(":", maxsplit=1)
        except ValueError:
            raise InvalidConfiguration(f"{line!r} is not a valid configuration line", lineno=lineno + 1)
        section[key.strip()] = value.strip()
    if section:
        yield first_line, section


def _contains_defaults(section: dict) -> bool:
    return any(key.startswith("default ") for key in section)


def _parse_defaults(section: dict) -> dict:
    return {key.split(" ", maxsplit=1)[1]: value for key, value in section.items() if key.startswith("default ")}


class InvalidConfiguration(Exception):
    def __init__(self, message=None, filename=None, lineno=None):
        self.filename = filename
        self.lineno = lineno
        super().__init__(message)

    def __str__(self):
        location = [item for item in (self.filename, self.lineno) if item]
        if location:
            location = ":".join(str(item) for item in location)
            return f"{location}: {super().__str__()}"
        return super().__str__()
