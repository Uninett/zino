"""Even-higher-level APIs over PySNMP's high-level APIs"""
import logging
import threading
from dataclasses import dataclass
from typing import Union

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
    oid: str
    value: Union[str, int]


class SNMP:
    """Represents an SNMP management session for a single device"""

    NON_REPEATERS = 0

    def __init__(self, device: PollDevice):
        self.device = device

    async def get(self, *oid: str) -> Union[MibObject, None]:
        """SNMP-GETs the given `oid`"""
        query = self._oid_to_objecttype(*oid)
        error_indication, error_status, error_index, var_binds = await getCmd(
            _get_engine(),
            self.community_data,
            self.udp_transport_target,
            ContextData(),
            query,
        )
        if self._handle_errors(error_indication, error_status, error_index, query):
            return

        for var_bind in var_binds:
            return MibObject(oid=var_bind[0], value=var_bind[1])

    def _handle_errors(self, error_indication: str, error_status: str, error_index: int, *query) -> bool:
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
        query = self._oid_to_objecttype(*oid)
        objecttype = await self._getnext(query)
        if not objecttype:
            return None
        return MibObject(oid=objecttype[0], value=objecttype[1])

    async def _getnext(self, oid_object: ObjectType) -> Union[ObjectType, None]:
        """SNMP-GETNEXTs the given ObjectType and returns the resulting ObjectType"""
        error_indication, error_status, error_index, var_binds = await nextCmd(
            _get_engine(),
            self.community_data,
            self.udp_transport_target,
            ContextData(),
            oid_object,
        )
        if self._handle_errors(error_indication, error_status, error_index, oid_object):
            return
        # var_binds should be a sequence of sequences with one inner sequence that contains the result.
        if var_binds and var_binds[0]:
            return var_binds[0][0]

    async def walk(self, *oid: str) -> list[MibObject]:
        """Uses SNMP-GETNEXT calls to get all objects in the subtree with `oid` as root"""
        current_object = self._oid_to_objecttype(*oid)
        self._resolve_object(current_object)
        original_oid = current_object[0]
        results = []
        while True:
            current_object = await self._getnext(current_object)
            if not current_object or not self._is_prefix_of_oid(original_oid, current_object[0]):
                break
            mibobject = MibObject(oid=current_object[0], value=current_object[1])
            results.append(mibobject)
        return results

    async def getbulk(self, *oid: str, max_repetitions: int = 1) -> list[MibObject]:
        """SNMP-BULKs the given `oid`"""
        oid_object = self._oid_to_objecttype(*oid)
        objecttypes = await self._getbulk(max_repetitions, oid_object)
        results = []
        for objecttype in objecttypes:
            mibobject = MibObject(oid=objecttype[0], value=objecttype[1])
            results.append(mibobject)
        return results

    async def _getbulk(self, max_repetitions: int, *oid_objects: ObjectType) -> list[ObjectType]:
        """SNMP-BULKs the given `oid_objects`"""
        error_indication, error_status, error_index, var_binds = await bulkCmd(
            _get_engine(),
            self.community_data,
            self.udp_transport_target,
            ContextData(),
            self.NON_REPEATERS,
            max_repetitions,
            *oid_objects,
        )
        if self._handle_errors(error_indication, error_status, error_index, *oid_objects):
            return []
        if not var_binds:
            return []
        return var_binds[0]

    async def bulkwalk(self, *oid: str, max_repetitions: int = 10) -> list[MibObject]:
        """Uses SNMP-BULK calls to get all objects in the subtree with `oid` as root"""
        query_object = self._oid_to_objecttype(*oid)
        self._resolve_object(query_object)
        start_oid = query_object[0]
        results = []
        while True:
            response = await self._getbulk(max_repetitions, query_object)
            if not response:
                break
            for result in response:
                if not self._is_prefix_of_oid(start_oid, result[0]):
                    return results
                query_object = result
                mibobject = MibObject(oid=result[0], value=result[1])
                results.append(mibobject)
        return results

    @classmethod
    def _is_prefix_of_oid(cls, prefix: str, oid: str) -> bool:
        """Returns True if `prefix` is a prefix of `oid` and not equal to it"""
        return len(oid) > len(prefix) and oid[: len(prefix)] == prefix

    @classmethod
    def _resolve_object(cls, object: ObjectType):
        engine = _get_engine()
        controller = engine.getUserContext("mibViewController")
        if not controller:
            controller = view.MibViewController(engine.getMibBuilder())
        object.resolveWithMib(controller)

    @classmethod
    def _oid_to_objecttype(cls, *oid: str) -> ObjectType:
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
