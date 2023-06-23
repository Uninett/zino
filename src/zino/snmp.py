"""Even-higher-level APIs over PySNMP's high-level APIs"""
import logging
import threading
from dataclasses import dataclass
from typing import Union

from pyasn1.type import univ
from pysnmp.hlapi.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    bulkCmd,
    getCmd,
    nextCmd,
)
from pysnmp.smi import view
from pysnmp.smi.error import MibNotFoundError

from zino.config.models import PollDevice

_log = logging.getLogger(__name__)

# keep track of variables that need to be local to the current thread
_local = threading.local()


def _get_engine():
    if not getattr(_local, "snmp_engine", None):
        _local.snmp_engine = SnmpEngine()
    return _local.snmp_engine


@dataclass
class MibObject:
    oid: tuple[int, ...]
    value: Union[str, int, tuple[int, ...]]


class SNMP:
    """Represents an SNMP management session for a single device"""

    NON_REPEATERS = 0

    def __init__(self, device: PollDevice):
        self.device = device

    async def get(self, *oid: str) -> Union[MibObject, None]:
        """SNMP-GETs the given `oid`"""
        query = self._oid_to_object_type(*oid)
        try:
            error_indication, error_status, error_index, var_binds = await getCmd(
                _get_engine(),
                self.community_data,
                self.udp_transport_target,
                ContextData(),
                query,
            )
        except MibNotFoundError as error:
            _log.error("%s: %s", self.device.name, error)
            return
        if self._handle_errors(error_indication, error_status, error_index, query):
            return
        for var_bind in var_binds:
            return self._object_type_to_mib_object(var_bind)

    def _handle_errors(self, error_indication: str, error_status: str, error_index: int, *query: ObjectType) -> bool:
        """Returns True if error occurred"""
        if error_indication:
            _log.error("%s: %s", self.device.name, error_indication)
            return True

        if error_status:
            _log.error(
                "%s: %s at %s",
                self.device.name,
                error_status.prettyPrint(),
                error_index and query[int(error_index) - 1][0] or "?",
            )
            return True
        return False

    async def getnext(self, *oid: str) -> Union[MibObject, None]:
        """SNMP-GETNEXTs the given `oid`"""
        query = self._oid_to_object_type(*oid)
        object_type = await self._getnext(query)
        if not object_type:
            return None
        return self._object_type_to_mib_object(object_type)

    async def _getnext(self, object_type: ObjectType) -> Union[ObjectType, None]:
        """SNMP-GETNEXTs the given `objecttype`"""
        try:
            error_indication, error_status, error_index, var_binds = await nextCmd(
                _get_engine(),
                self.community_data,
                self.udp_transport_target,
                ContextData(),
                object_type,
            )
        except MibNotFoundError as error:
            _log.error("%s: %s", self.device.name, error)
            return
        if self._handle_errors(error_indication, error_status, error_index, object_type):
            return
        # var_binds should be a sequence of sequences with one inner sequence that contains the result.
        if var_binds and var_binds[0]:
            return var_binds[0][0]

    async def walk(self, *oid: str) -> list[MibObject]:
        """Uses SNMP-GETNEXT calls to get all objects in the subtree with `oid` as root"""
        results = []
        current_object = self._oid_to_object_type(*oid)
        try:
            self._resolve_object(current_object)
        except MibNotFoundError as error:
            _log.error("%s: %s", self.device.name, error)
            return results
        original_oid = str(current_object[0])
        while True:
            current_object = await self._getnext(current_object)
            if not current_object or not self._is_prefix_of_oid(original_oid, str(current_object[0])):
                break
            mib_object = self._object_type_to_mib_object(current_object)
            results.append(mib_object)
        return results

    async def getbulk(self, *oid: str, max_repetitions: int = 1) -> list[MibObject]:
        """SNMP-BULKs the given `oid`"""
        oid_object = self._oid_to_object_type(*oid)
        objecttypes = await self._getbulk(max_repetitions, oid_object)
        results = []
        for objecttype in objecttypes:
            mibobject = self._object_type_to_mib_object(objecttype)
            results.append(mibobject)
        return results

    async def _getbulk(self, max_repetitions: int, object_type: ObjectType) -> list[ObjectType]:
        """SNMP-BULKs the given `oid_object`"""
        try:
            error_indication, error_status, error_index, var_binds = await bulkCmd(
                _get_engine(),
                self.community_data,
                self.udp_transport_target,
                ContextData(),
                self.NON_REPEATERS,
                max_repetitions,
                object_type,
            )
        except MibNotFoundError as error:
            _log.error("%s: %s", self.device.name, error)
            return []
        if self._handle_errors(error_indication, error_status, error_index, object_type):
            return []
        if not var_binds:
            return []
        return var_binds[0]

    async def bulkwalk(self, *oid: str, max_repetitions: int = 10) -> list[MibObject]:
        """Uses SNMP-BULK calls to get all objects in the subtree with `oid` as root"""
        results = []
        query_object = self._oid_to_object_type(*oid)
        try:
            self._resolve_object(query_object)
        except MibNotFoundError as error:
            _log.error("%s: %s", self.device.name, error)
            return results
        start_oid = str(query_object[0])
        while True:
            response = await self._getbulk(max_repetitions, query_object)
            if not response:
                break
            for result in response:
                if not self._is_prefix_of_oid(start_oid, str(result[0])):
                    return results
                query_object = result
                mib_object = self._object_type_to_mib_object(result)
                results.append(mib_object)
        return results

    @classmethod
    def _object_type_to_mib_object(cls, object_type: ObjectType) -> MibObject:
        oid_tuple = object_type[0].getOid().asTuple()
        value = object_type[1]
        if isinstance(value, univ.Integer):
            value = int(value)
        elif isinstance(value, univ.OctetString):
            value = str(value)
        elif isinstance(value, ObjectIdentity):
            value = value.getOid().asTuple()
        else:
            raise ValueError(f"Could not convert unknown type {type(value)}")
        return MibObject(oid_tuple, value)

    @classmethod
    def _is_prefix_of_oid(cls, prefix: str, oid: str) -> bool:
        """Returns True if `prefix` is a prefix of `oid` and not equal to it"""
        return len(oid) > len(prefix) and oid[: len(prefix)] == prefix

    @classmethod
    def _resolve_object(cls, object_type: ObjectType):
        """Raises MibNotFoundError if oid in `object` can not be found"""
        engine = _get_engine()
        controller = engine.getUserContext("mibViewController")
        if not controller:
            controller = view.MibViewController(engine.getMibBuilder())
        object_type.resolveWithMib(controller)

    @classmethod
    def _oid_to_object_type(cls, *oid: str) -> ObjectType:
        return ObjectType(ObjectIdentity(*oid))

    @property
    def mp_model(self) -> int:
        """Returns the preferred SNMP version of this device as a PySNMP mpModel value"""
        return 1 if self.device.hcounters else 0

    @property
    def community_data(self) -> CommunityData:
        return CommunityData(self.device.community, mpModel=self.mp_model)

    @property
    def udp_transport_target(self) -> UdpTransportTarget:
        return UdpTransportTarget((str(self.device.address), self.device.port))
