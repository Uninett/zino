from dataclasses import dataclass
from typing import Optional


@dataclass
class LineData:
    """Flexible definition of the value and identifiers found in a Zino1 .tcl state dump.
    Each line in the state dump can contain several identifiers but there is always only one value.
    """

    identifiers: Optional[tuple[str, ...]]
    value: str


def get_line_data(line) -> LineData:
    """Parses a line from a Zino1 .tcl filedump into a LineData object
    containing useful information
    """
    try:
        identifiers = get_identifiers(line)
    except IndexError:
        identifiers = None
    value = get_value(line)
    return LineData(value=value, identifiers=identifiers)


def get_identifiers(line: str) -> tuple[str, ...]:
    # removes part of line before identifiers are defined
    split_line = line.split("(")[1]
    # removes everything after the identifiers
    split_line = split_line.split(")")[0]
    identifiers = split_line.split(",")
    if line.startswith("set ::EventAttrs_") or line.startswith("set ::pm::event_"):
        # remove everything before the event ID starts
        event_line = line.split("_")[1]
        # remove everything after event ID
        event_id = event_line.split("(")[0]
        identifiers.append(event_id)
    return tuple(identifiers)


def get_value(line: str) -> str:
    # remove everything before the value is defined
    value = line.split(" ")[2:]
    value = " ".join(value)
    # strip whitespace and quotes
    value = value.strip(' "')
    return value
