"""Even-higher-level APIs over PySNMP's high-level APIs"""
import logging
import os
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, NamedTuple, Sequence, Union

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
from pysnmp.smi import builder, view
from pysnmp.smi.error import MibNotFoundError

from zino.config.models import PollDevice
from zino.oid import OID

_log = logging.getLogger(__name__)

# keep track of variables that need to be local to the current thread
_local = threading.local()

MIB_SOURCE_DIR = os.path.join(os.path.dirname(__file__), "mibdumps")


def _get_engine():
    if not getattr(_local, "snmp_engine", None):
        _local.snmp_engine = SnmpEngine()
        mib_builder = _local.snmp_engine.getMibBuilder()
        mib_builder.addMibSources(builder.DirMibSource(MIB_SOURCE_DIR))
    return _local.snmp_engine


@dataclass
class MibObject:
    oid: OID
    value: Union[str, int, OID]


class Identifier(NamedTuple):
    """Identifies a MIB object by MIB, object name and row index"""

    mib: str
    object: str
    index: OID


PySNMPVarBind = tuple[ObjectIdentity, ObjectType]
SNMPVarBind = tuple[Identifier, Any]
SupportedTypes = Union[univ.Integer, univ.OctetString, ObjectIdentity, ObjectType]


class SNMP:
    """Represents an SNMP management session for a single device"""

    NON_REPEATERS = 0

    def __init__(self, device: PollDevice):
        self.device = device

    async def get(self, *oid: str) -> Union[MibObject, None]:
        """SNMP-GETs the given oid
        Example usage:
            get("SNMPv2-MIB", "sysUpTime", 0)
            get("1.3.6.1.2.1.1.3.0")

        :param oid: Values for defining an OID. For detailed use see
            https://github.com/pysnmp/pysnmp/blob/bc1fb3c39764f36c1b7c9551b52ef8246b9aea7c/pysnmp/smi/rfc1902.py#L35-L49
        :return: A MibObject representing the resulting MIB variable or None if nothing could be found
        """
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
        """SNMP-GETNEXTs the given oid
        Example usage:
            getnext("SNMPv2-MIB", "sysUpTime")
            getnext("1.3.6.1.2.1.1.3")

        :param oid: Values for defining an OID. For detailed use see
            https://github.com/pysnmp/pysnmp/blob/bc1fb3c39764f36c1b7c9551b52ef8246b9aea7c/pysnmp/smi/rfc1902.py#L35-L49
        :return: A MibObject representing the resulting MIB variable or None if nothing could be found
        """
        query = self._oid_to_object_type(*oid)
        object_type = await self._getnext(query)
        if not object_type:
            return None
        return self._object_type_to_mib_object(object_type)

    async def _getnext(self, object_type: ObjectType) -> Union[ObjectType, None]:
        """SNMP-GETNEXTs the given object_type

        :param object_type: An ObjectType representing the object you want to query
        :return: An ObjectType representing the resulting MIB variable or None if nothing could be found
        """
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
        """Uses SNMP-GETNEXT calls to get all objects in the subtree with oid as root
        Example usage:
            walk("IF-MIB", "ifName")
            walk("1.3.6.1.2.1.31.1.1.1.1")

        :param oid: Values for defining an OID. For detailed use see
            https://github.com/pysnmp/pysnmp/blob/bc1fb3c39764f36c1b7c9551b52ef8246b9aea7c/pysnmp/smi/rfc1902.py#L35-L49
        :return: A list of MibObjects representing the resulting MIB variables
        """
        results = []
        current_object = self._oid_to_object_type(*oid)
        try:
            self._resolve_object(current_object)
        except MibNotFoundError as error:
            _log.error("%s: %s", self.device.name, error)
            return results
        original_oid = OID(str(current_object[0]))
        while True:
            current_object = await self._getnext(current_object)
            if not current_object or not original_oid.is_a_prefix_of(str(current_object[0])):
                break
            mib_object = self._object_type_to_mib_object(current_object)
            results.append(mib_object)
        return results

    async def getbulk(self, *oid: str, max_repetitions: int = 1) -> list[MibObject]:
        """SNMP-BULKs the given oid
        Example usage:
            getbulk("IF-MIB", "ifName", max_repetitions=5)
            getbulk("1.3.6.1.2.1.31.1.1.1.1")

        :param oid: Values for defining an OID. For detailed use see
            https://github.com/pysnmp/pysnmp/blob/bc1fb3c39764f36c1b7c9551b52ef8246b9aea7c/pysnmp/smi/rfc1902.py#L35-L49
        :param max_repetitions: Max amount of MIB objects to retrieve
        :return: A list of MibObjects representing the resulting MIB variables
        """
        oid_object = self._oid_to_object_type(*oid)
        objecttypes = await self._getbulk(oid_object, max_repetitions)
        results = []
        for objecttype in objecttypes:
            mibobject = self._object_type_to_mib_object(objecttype)
            results.append(mibobject)
        return results

    async def _getbulk(self, object_type: ObjectType, max_repetitions: int) -> list[ObjectType]:
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

    async def getbulk2(self, *variables: Sequence[str], max_repetitions: int = 10) -> Sequence[Sequence[SNMPVarBind]]:
        """Issues a GET-BULK request for a set of multiple variables, returning the response in a slightly different
         format than getbulk.

        Example usage:
            >>> snmp = SNMP(...)
            >>> snmp.getbulk2(("IF-MIB", "ifName"), ("IF-MIB", "ifAlias"), max_repetitions=5)
            [[(Identifier(mib='IF-MIB', object='ifAlias', index=OID('.1')), 'Uplink'),
              (Identifier(mib='IF-MIB', object='ifDescr', index=OID('.1')), 'GigabitEthernet0/1')],
             [(Identifier(mib='IF-MIB', object='ifAlias', index=OID('.2')), 'example-sw.example.org'),
              (Identifier(mib='IF-MIB', object='ifDescr', index=OID('.2')), 'GigabitEthernet0/2')]]

        :param variables: Variables to fetch, either as OIDs or symbolic names
        :param max_repetitions: Max amount of MIB objects to retrieve
        :return: A sequence of two-tuples that represent the response varbinds
        """
        oid_objects = [self._oid_to_object_type(*var) for var in variables]
        var_bind_table = await self._getbulk2(*oid_objects, max_repetitions=max_repetitions)

        return [[_convert_varbind(i, v) for i, v in var_binds] for var_binds in var_bind_table]

    async def _getbulk2(
        self, *variables: Sequence[ObjectType], max_repetitions: int
    ) -> Sequence[Sequence[PySNMPVarBind]]:
        """Issues a GET-BULK request for one or more variables, returning the raw var bind table from PySNMP"""
        try:
            error_indication, error_status, error_index, var_bind_table = await bulkCmd(
                _get_engine(),
                self.community_data,
                self.udp_transport_target,
                ContextData(),
                self.NON_REPEATERS,
                max_repetitions,
                *variables,
            )
        except MibNotFoundError as error:
            _log.error("%s: %s", self.device.name, error)
            return []
        if self._handle_errors(error_indication, error_status, error_index, *variables):
            return []
        return var_bind_table or []

    async def bulkwalk(self, *oid: str, max_repetitions: int = 10) -> list[MibObject]:
        """Uses SNMP-BULK calls to get all objects in the subtree with oid as root
        Example usage:
            bulkwalk("IF-MIB", "ifName", max_repetitions=5)
            bulkwalk("1.3.6.1.2.1.31.1.1.1.1")

        :param oid: Values for defining an OID. For detailed use see
            https://github.com/pysnmp/pysnmp/blob/bc1fb3c39764f36c1b7c9551b52ef8246b9aea7c/pysnmp/smi/rfc1902.py#L35-L49
        :param max_repetitions: Max amount of MIB objects to retrieve per SNMP-BULK call
        :return: A list of MibObjects representing the resulting MIB variables
        """
        results = []
        query_object = self._oid_to_object_type(*oid)
        try:
            self._resolve_object(query_object)
        except MibNotFoundError as error:
            _log.error("%s: %s", self.device.name, error)
            return results
        start_oid = OID(str(query_object[0]))
        while True:
            response = await self._getbulk(query_object, max_repetitions)
            if not response:
                break
            for result in response:
                if not start_oid.is_a_prefix_of(str(result[0])):
                    return results
                query_object = result
                mib_object = self._object_type_to_mib_object(result)
                results.append(mib_object)
        return results

    async def sparsewalk(self, *variables: Sequence[str], max_repetitions: int = 10) -> dict[OID, dict[str, Any]]:
        """Bulkwalks and returns a "sparse" table.

        A sparse walk is just a walk operation that returns selected columns of table (or, from multiple tables that
        augment each other).

        Example usage:
            >>> snmp = SNMP(...)
            >>> snmp.sparsewalk(("IF-MIB", "ifName"), ("IF-MIB", "ifAlias"))
            {OID('.1'): {"ifname": "1", "ifAlias": "uplink"},
             OID('.2'): {"ifName": "2", "ifAlias": "next-sw.example.org"}}
        """
        query_objects = [self._oid_to_object_type(*var) for var in variables]
        try:
            [self._resolve_object(obj) for obj in query_objects]
        except MibNotFoundError as error:
            _log.error("%s: %s", self.device.name, error)
            return {}

        roots = [OID(o[0]) for o in query_objects]  # used to determine which responses are in scope
        results: dict[OID, dict[str, Any]] = defaultdict(dict)

        def _var_bind_is_in_scope(var: PySNMPVarBind) -> bool:
            oid = OID(var[0])
            return any(root.is_a_prefix_of(oid) for root in roots)

        while True:
            var_bind_table = await self._getbulk2(*query_objects, max_repetitions=max_repetitions)
            if not var_bind_table:
                break

            # Integrate response values into result dict
            for var_binds in var_bind_table:
                for var_bind in var_binds:
                    if _var_bind_is_in_scope(var_bind):
                        ident, value = _convert_varbind(*var_bind)
                        results[ident.index][ident.object] = value

            # Build next set of query objects from last result row
            query_objects = [v for v in var_binds if _var_bind_is_in_scope(v)]
        return dict(results)

    @staticmethod
    def _object_type_to_mib_object(object_type: ObjectType) -> MibObject:
        oid = OID(str(object_type[0]))
        value = _mib_value_to_python(object_type[1])
        return MibObject(oid, value)

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


def _convert_varbind(ident: ObjectIdentity, value: ObjectType) -> SNMPVarBind:
    """Converts a PySNMP varbind pair to an Identifier/value pair"""
    mib, obj, row_index = ident.getMibSymbol()
    value = _mib_value_to_python(value)
    return Identifier(mib, obj, OID(row_index)), value


def _mib_value_to_python(value: SupportedTypes) -> Union[str, int, OID]:
    """Translates various PySNMP mib value objects to plainer Python objects, such as strings, integers or OIDs"""
    if isinstance(value, univ.Integer):
        value = int(value) if not value.namedValues else value.prettyPrint()
    elif isinstance(value, univ.OctetString):
        value = str(value)
    elif isinstance(value, ObjectIdentity):
        value = OID(str(value))
    else:
        raise ValueError(f"Could not convert unknown type {type(value)}")
    return value
