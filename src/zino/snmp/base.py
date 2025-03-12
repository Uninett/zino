"""Base SNMP functionality and types shared by all back-ends"""

from dataclasses import dataclass
from typing import Any, NamedTuple, Union

from zino.oid import OID


@dataclass
class MibObject:
    oid: OID
    value: Union[str, int, OID]


class Identifier(NamedTuple):
    """Identifies a MIB object by MIB, object name and row index"""

    mib: str
    object: str
    index: OID


SNMPVarBind = tuple[Identifier, Any]
SparseWalkResponse = dict[OID, dict[str, Any]]


class SnmpError(Exception):
    """Base class for SNMP, MIB and OID specific errors"""


class ErrorIndication(SnmpError):
    """Class for SNMP errors that occur locally,
    as opposed to being reported from a different SNMP entity.
    """


class MibNotFoundError(ErrorIndication):
    """Raised if a required MIB file could not be found"""


class ErrorStatus(SnmpError):
    """Raised if an SNMP entity includes a non-zero error status in its response PDU.
    RFC 1905 defines the possible errors that can be specified in the error status field.
    This can either be used directly or subclassed for one of these specific errors.
    """


class NoSuchNameError(ErrorStatus):
    """Represents the "noSuchName" error. Raised if an object could not be found at an OID."""


class VarBindError(SnmpError):
    """Base class for errors carried in varbinds and not in the errorStatus or errorIndication fields"""


class NoSuchObjectError(VarBindError):
    """Raised if an object could not be found at an OID"""


class NoSuchInstanceError(VarBindError):
    """Raised if an instance could not be found at an OID"""


class EndOfMibViewError(VarBindError):
    """Raised if end of MIB view is encountered"""
