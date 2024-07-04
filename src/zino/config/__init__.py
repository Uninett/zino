from typing import Optional

try:
    from tomllib import TOMLDecodeError, load
except ImportError:
    from tomli import TOMLDecodeError, load

from .models import Configuration


class InvalidConfigurationError(Exception):
    """The configuration file is invalid toml"""


def read_configuration(config_file_name: Optional[str] = None, poll_file_name: Optional[str] = None) -> Configuration:
    """
    Reads and validates config toml file

    Returns configuration if file name is given and file exists, returns a
    configuration with the default values if no file name is given

    Raises InvalidConfigurationError if toml file is invalid,
    OSError if the config toml file could not be found and
    pydantic.ValidationError if values in it are invalid or the specified files
    don't exist
    """
    if not config_file_name:
        return Configuration()

    with open(config_file_name, mode="rb") as cf:
        try:
            config_dict = load(cf)
        except TOMLDecodeError:
            raise InvalidConfigurationError

    # Polldevs by command line argument will override config file entry
    if poll_file_name:
        if "polling" not in config_dict.keys():
            config_dict["polling"] = {"file": poll_file_name}
        else:
            config_dict["polling"]["file"] = poll_file_name

    config = Configuration.model_validate(obj=config_dict, strict=True)

    return config
