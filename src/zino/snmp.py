"""Even-higher-level APIs over PySNMP's high-level APIs"""
import logging
import threading

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

from zino.config.models import PollDevice

_log = logging.getLogger(__name__)

# keep track of variables that need to be local to the current thread
_local = threading.local()


def _get_engine():
    if not getattr(_local, "snmp_engine", None):
        _local.snmp_engine = SnmpEngine()
    return _local.snmp_engine


class SNMP:
    """Represents an SNMP management session for a single device"""

    def __init__(self, device: PollDevice):
        self.device = device

    async def get(self, *oid):
        """SNMP-GETs a single value"""
        query = [ObjectType(ObjectIdentity(*oid))]
        error_indication, error_status, error_index, var_binds = await getCmd(
            _get_engine(),
            self.community_data,
            self.udp_transport_target,
            ContextData(),
            *query,
        )
        if self._handle_errors(error_indication, error_status, error_index, query):
            return

        for var_bind in var_binds:
            _, value = var_bind
            return value

    def _handle_errors(self, error_indication, error_status, error_index, *query):
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

    async def getnext(self, *oid):
        """SNMP-GETNEXTs the given `oid` and returns the resulting ObjectType"""
        query = ObjectType(ObjectIdentity(*oid))
        return await self._getnext(query)

    async def _getnext(self, oid_object: ObjectType):
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

    async def walk(self, *oid):
        """Uses SNMP-GETNEXT calls to get all ObjectTypes in the subtree with `oid` as root"""
        current_object = ObjectType(ObjectIdentity(*oid))
        self._resolve_object(current_object)
        original_oid = current_object[0]
        results = []
        while True:
            current_object = await self._getnext(current_object)
            if not current_object or not self._is_prefix_of_oid(original_oid, current_object[0]):
                break
            results.append(current_object)
        return results

    async def getbulk(self, *oid, non_repeaters=0, max_repetitions=1):
        """SNMP-BULKs the given `oid` and returns the resulting ObjectTypes"""
        oid_object = ObjectType(ObjectIdentity(*oid))
        return await self._bulk(non_repeaters, max_repetitions, oid_object)

    async def _getbulk(self, non_repeaters, max_repetitions, *oid_objects):
        """SNMP-BULKs the given `oid_objects` and returns the resulting ObjectTypes"""
        error_indication, error_status, error_index, var_binds = await bulkCmd(
            _get_engine(),
            self.community_data,
            self.udp_transport_target,
            ContextData(),
            non_repeaters,
            max_repetitions,
            *oid_objects,
        )
        if self._handle_errors(error_indication, error_status, error_index, *oid_objects):
            return
        return var_binds

    async def bulkwalk(self, *oid, max_repetitions=10):
        """Uses SNMP-BULK calls to get all ObjectTypes in the subtree with `oid` as root"""
        query_object = ObjectType(ObjectIdentity(*oid))
        self._resolve_object(query_object)
        start_oid = query_object[0]
        results = []
        while True:
            response = await self._bulk(0, max_repetitions, query_object)
            if not response or not response[0]:
                break
            for result in response[0]:
                if not self._is_prefix_of_oid(start_oid, result[0]):
                    return results
                results.append(result)
                query_object = result
        return results

    def _is_prefix_of_oid(self, prefix, oid):
        """Returns True if `prefix` is a prefix of `oid` and not equal to it"""
        return len(oid) > len(prefix) and oid[: len(prefix)] == prefix

    def _resolve_object(self, object: ObjectType):
        controller = _get_engine().getUserContext("mibViewController")
        object.resolveWithMib(controller)

    @property
    def mp_model(self):
        """Returns the preferred SNMP version of this device as a PySNMP mpModel value"""
        return 1 if self.device.hcounters else 0

    @property
    def community_data(self):
        return CommunityData(self.device.community, mpModel=self.mp_model)

    @property
    def udp_transport_target(self):
        return UdpTransportTarget((str(self.device.address), self.device.port))
