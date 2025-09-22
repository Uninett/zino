"""Zino configuration models"""

from ipaddress import IPv4Address, IPv6Address
from os import R_OK, access
from os.path import isfile
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict
from pydantic.functional_validators import AfterValidator
from typing_extensions import Annotated

DEFAULT_INTERVAL_MINUTES = 5
STATE_FILENAME = "zino-state.json"
EVENT_DUMP_DIR = "old-events"
POLLFILE = "polldevs.cf"

IPAddress = Union[IPv4Address, IPv6Address]


def validate_file_can_be_opened(filename: str) -> str:
    assert isfile(filename) and access(filename, R_OK), f"File {filename} doesn't exist or isn't readable"
    return filename


ExistingFileName = Annotated[str, AfterValidator(validate_file_can_be_opened)]


# config fields and default values from
# https://gitlab.sikt.no/verktoy/zino/blob/master/common/config.tcl#L18-44
class PollDevice(BaseModel):
    """Defines the attributes Zino needs/wants to be able to poll a device"""

    name: str
    address: IPAddress
    community: str = "public"
    dns: str = None
    interval: int = DEFAULT_INTERVAL_MINUTES
    ignorepat: Optional[str] = None
    watchpat: Optional[str] = None
    priority: int = 100
    timeout: int = 5
    retries: int = 3
    domain: str = None
    statistics: bool = True
    hcounters: bool = True  # Not used but kept for compatibility with old config files
    snmpversion: Literal["v1", "v2c"] = "v2c"
    do_bgp: bool = True
    port: int = 161


class Archiving(BaseModel):
    model_config = ConfigDict(extra="forbid")

    old_events_dir: str = EVENT_DUMP_DIR


class Authentication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: ExistingFileName = "secrets"


class Persistence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: str = STATE_FILENAME
    period: int = DEFAULT_INTERVAL_MINUTES


class Polling(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: ExistingFileName = POLLFILE
    period: int = 1


class TrapConfiguration(BaseModel):
    """Trap reception configuration"""

    model_config = ConfigDict(extra="forbid")

    require_community: list[str] = ["public", "secret"]


class SNMPConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: Literal["pysnmp", "netsnmp"] = "netsnmp"
    trap: TrapConfiguration = TrapConfiguration()


class EventConfiguration(BaseModel):
    """Options to control how events are created"""

    model_config = ConfigDict(extra="forbid")

    make_events_for_new_interfaces: bool = False


class Configuration(BaseModel):
    """Class for keeping track of the configuration set by zino.toml"""

    # throw ValidationError on extra keys
    model_config = ConfigDict(extra="forbid")

    archiving: Archiving = Archiving()
    authentication: Authentication = Authentication()
    persistence: Persistence = Persistence()
    polling: Polling = Polling()
    snmp: SNMPConfiguration = SNMPConfiguration()
    event: EventConfiguration = EventConfiguration()
    logging: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {
            "root": {"level": "INFO", "handlers": ["console"]},
            "apscheduler": {"level": "WARNING"},
        },
        "formatters": {"standard": {"format": "%(asctime)s - %(levelname)s - %(name)s (%(threadName)s) - %(message)s"}},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stderr",
            }
        },
    }
