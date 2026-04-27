import re
from difflib import get_close_matches
from typing import Optional

try:
    from tomllib import TOMLDecodeError, load
except ImportError:
    from tomli import TOMLDecodeError, load

from pydantic import BaseModel, ValidationError

from .models import Configuration


class InvalidConfigurationError(Exception):
    """The configuration file is invalid toml"""


def read_configuration(config_file_name: str, poll_file_name: Optional[str] = None) -> Configuration:
    """
    Reads and validates config toml file

    Returns configuration if file name is given and file exists

    Raises InvalidConfigurationError if toml file is invalid,
    OSError if the config toml file could not be found and
    pydantic.ValidationError if values in it are invalid or the specified files
    don't exist
    """
    with open(config_file_name, mode="rb") as cf:
        try:
            config_dict = load(cf)
        except TOMLDecodeError as error:
            raise InvalidConfigurationError(str(error)) from error

    # Polldevs by command line argument will override config file entry
    if poll_file_name:
        if "polling" not in config_dict.keys():
            config_dict["polling"] = {"file": poll_file_name}
        else:
            config_dict["polling"]["file"] = poll_file_name

    config = Configuration.model_validate(obj=config_dict, strict=True)

    return config


_TYPE_NAMES = {
    "int_type": "int",
    "float_type": "float",
    "bool_type": "bool",
    "string_type": "str",
}


def format_validation_error(error: ValidationError, model: type[BaseModel] = Configuration) -> list[str]:
    """Format a Pydantic ValidationError into operator-friendly messages.

    :param error: The Pydantic ValidationError raised by config validation.
    :param model: The root model the error was raised against. Used to look up
        valid sibling field names when suggesting alternatives for misspelled
        keys.
    :return: One human-readable message per entry in ``error.errors()``.
    """
    return [_format_single_error(detail, model) for detail in error.errors()]


def _format_single_error(detail: dict, model: type[BaseModel]) -> str:
    loc = detail.get("loc", ())
    dotted = _format_loc(loc)
    err_type = detail.get("type", "")

    if err_type == "extra_forbidden":
        return _format_unknown_key(loc, dotted, model)
    if err_type == "missing":
        return f"Missing required configuration key '{dotted}'"
    if err_type == "literal_error":
        return _format_literal_error(detail, dotted)
    if err_type in _TYPE_NAMES:
        return _format_type_error(detail, err_type, dotted)
    if err_type == "assertion_error":
        cleaned = re.sub(r"^Assertion failed,\s*", "", detail.get("msg", ""))
        return f"Invalid value for '{dotted}': {cleaned}"
    return f"Invalid configuration at '{dotted}': {detail.get('msg', '')}"


def _format_loc(loc: tuple) -> str:
    """Render a Pydantic error location tuple as a dotted path with [i] for list indices."""
    parts = []
    for part in loc:
        if isinstance(part, int):
            parts.append(f"[{part}]")
        elif parts:
            parts.append(f".{part}")
        else:
            parts.append(str(part))
    return "".join(parts)


def _format_unknown_key(loc: tuple, dotted: str, model: type[BaseModel]) -> str:
    base = f"Unknown configuration key '{dotted}'"
    parent = _resolve_model(model, loc[:-1])
    if parent is None:
        return base
    suggestions = get_close_matches(str(loc[-1]), list(parent.model_fields.keys()), n=1)
    if suggestions:
        return f"{base}. Did you mean '{suggestions[0]}'?"
    return base


def _format_literal_error(detail: dict, dotted: str) -> str:
    expected = detail.get("ctx", {}).get("expected", "")
    user_input = detail.get("input")
    return f"Invalid value {user_input!r} for '{dotted}'; must be one of: {expected}"


def _format_type_error(detail: dict, err_type: str, dotted: str) -> str:
    wanted = _TYPE_NAMES[err_type]
    user_input = detail.get("input")
    return f"Configuration key '{dotted}' must be of type {wanted}, got {user_input!r}"


def _resolve_model(model: type[BaseModel], path: tuple) -> Optional[type[BaseModel]]:
    """Walk down ``path`` from ``model``, returning the BaseModel at the end.

    Returns None if the path encounters a non-BaseModel field. Optional/Union
    submodels are not traversed; suggestions will simply not appear for keys
    inside them.
    """
    current = model
    for part in path:
        field = current.model_fields.get(str(part))
        if field is None:
            return None
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            current = annotation
        else:
            return None
    return current
