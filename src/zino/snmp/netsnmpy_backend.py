"""SNMP back-end based on netsnmp-cffi"""

import logging
from collections import defaultdict
from typing import Any, Optional, Sequence, Tuple, Union

from netsnmpy import netsnmp
from netsnmpy.netsnmp import (
    EndOfMibView,
    NoSuchInstance,
    NoSuchObject,
    ObjectIdentifier,
    SNMPVariable,
    symbol_to_oid,
)
from netsnmpy.session import SNMPSession

from zino.config.models import PollDevice
from zino.oid import OID
from zino.snmp.base import (
    EndOfMibViewError,
    Identifier,
    MibNotFoundError,
    MibObject,
    NoSuchInstanceError,
    NoSuchObjectError,
    SNMPVarBind,
    SparseWalkResponse,
)

_log = logging.getLogger(__name__)


def get_new_snmp_engine():
    """This is only here because the pysnmp backend provides it.  It needs to be
    gone, but we need to figure out how it is used outside this module, if at all.
    """
    raise NotImplementedError


class SNMP:
    """Represents an SNMP management session for a single device"""

    def __init__(self, device: PollDevice):
        self.device = device
        self.session: SNMPSession = SNMPSession(
            host=device.address,
            port=device.port,
            community=device.community,
            version=self.snmp_version,
            timeout=device.timeout,
            retries=device.retries,
        )
        self.session.open()

    async def get(self, *oid: str) -> MibObject:
        """SNMP-GETs the given oid
        Example usage:
            get("SNMPv2-MIB", "sysUpTime", 0)
            get("1.3.6.1.2.1.1.3.0")

        :param oid: Symbolic MIB object to query.  Multiple formats supported.
        :return: A MibObject representing the resulting MIB variable
        """
        objid = resolve_symbol(oid)
        var_binds = await self.session.aget(objid)
        result = var_binds[0]
        self._raise_varbind_errors(result)
        return MibObject(*result)

    async def get2(self, *variables: Sequence[Union[str, int]]) -> list[SNMPVarBind]:
        """SNMP-GETs multiple variables

        Example usage:
            get2(("SNMPv2-MIB", "sysUpTime", 0), ("SNMPv2-MIB", "sysDescr", 0))
            get2(("1.3.6.1.2.1.1.3.0",))

        :param variables: Symbolic MIB object to query.  Multiple formats supported.
        :return: A list of MibObject instances representing the resulting MIB variables
        """
        oids = [resolve_symbol(var) for var in variables]
        var_binds = await self.session.aget(*oids)
        return [_convert_snmp_variable(v) for v in var_binds]

    def _raise_varbind_errors(self, var_bind: netsnmp.Variable):
        """Raises a relevant exception if an error has occurred in a varbind"""
        oid, value = var_bind
        if isinstance(value, NoSuchObject):
            raise NoSuchObjectError(f"Could not find object at {oid}")
        if isinstance(value, NoSuchInstance):
            raise NoSuchInstanceError(f"Could not find instance at {oid}")
        if isinstance(value, EndOfMibView):
            raise EndOfMibViewError("Reached end of MIB view")

    async def getnext(self, *oid: str) -> MibObject:
        """SNMP-GETNEXTs the given oid
        Example usage:
            getnext("SNMPv2-MIB", "sysUpTime")
            getnext("1.3.6.1.2.1.1.3")

        :param oid: Symbolic MIB object to query.  Multiple formats supported.
        :return: A MibObject representing the resulting MIB variable
        """
        objid = resolve_symbol(oid)
        var_binds = await self.session.agetnext(objid)
        result = var_binds[0]
        self._raise_varbind_errors(result)
        if result.enum_value is not None:
            value = result.enum_value
        else:
            value = result.value
        return MibObject(result.oid, value)

    async def getnext2(self, *variables: Sequence[str]) -> list[SNMPVarBind]:
        """Dispatches a GET-NEXT query for the given variables and returns a result where the fetched variables are
        identified symbolically.

        Example usage:
        >>> await s.getnext2(("IF-MIB", "ifName", "1"), ("IF-MIB", "ifAlias", "1"])
        [(Identifier("IF-MIB", "ifName", OID('.2')), "Gi2/3"),
         (Identifier("IF-MIB", "ifName", OID('.2')), "Uplink to somewhere")]
        >>>

        :param variables: Symbolic MIB objects to query.  Multiple formats supported.
        :return: A sequence of MibObject instances representing the resulting MIB variables
        """
        oids = [resolve_symbol(var) for var in variables]
        var_binds = await self.session.agetnext(*oids)
        return [_convert_snmp_variable(v) for v in var_binds]

    async def walk(self, *oid: str) -> list[MibObject]:
        """Uses SNMP-GETNEXT calls to get all objects in the subtree with oid as root
        Example usage:
            walk("IF-MIB", "ifName")
            walk("1.3.6.1.2.1.31.1.1.1.1")

        :param oid: Symbolic MIB object to query.  Multiple formats supported.
        :return: A list of MibObjects representing the resulting MIB variables
        """
        results = []
        root_oid = resolve_symbol(oid)
        current_oid = root_oid
        while True:
            response = await self.session.agetnext(current_oid)
            var_bind = response[0]
            current_oid, value = var_bind
            if not root_oid.is_a_prefix_of(current_oid):
                break
            results.append(MibObject(current_oid, value))
        return results

    async def getbulk(self, *oid: str, max_repetitions: int = 1) -> list[MibObject]:
        """SNMP-BULKs the given oid
        Example usage:
            getbulk("IF-MIB", "ifName", max_repetitions=5)
            getbulk("1.3.6.1.2.1.31.1.1.1.1")

        :param oid: Symbolic MIB object to query.  Multiple formats supported.
        :param max_repetitions: Max amount of MIB objects to retrieve
        :return: A list of MibObjects representing the resulting MIB variables
        """
        objid = resolve_symbol(oid)
        var_binds = await self.session.agetbulk(objid, max_repetitions=max_repetitions)
        return [MibObject(*var_bind) for var_bind in var_binds]

    async def getbulk2(self, *variables: Sequence[str], max_repetitions: int = 10) -> list[list[SNMPVarBind]]:
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
        oid_objects = [resolve_symbol(v) for v in variables]
        var_binds = await self.session.agetbulk(*oid_objects, max_repetitions=max_repetitions)

        query_count = len(variables)
        response_chunks = (var_binds[i : i + query_count] for i in range(0, len(var_binds), query_count))

        return [[_convert_snmp_variable(var_bind) for var_bind in chunk] for chunk in response_chunks]

    async def bulkwalk(self, *oid: str, max_repetitions: int = 10) -> list[MibObject]:
        """Uses SNMP-BULK calls to get all objects in the subtree with oid as root
        Example usage:
            bulkwalk("IF-MIB", "ifName", max_repetitions=5)
            bulkwalk("1.3.6.1.2.1.31.1.1.1.1")

        :param oid: Symbolic MIB object to query.  Multiple formats supported.
        :param max_repetitions: Max amount of MIB objects to retrieve per SNMP-BULK call
        :return: A list of MibObjects representing the resulting MIB variables
        """
        results = []
        start_oid = query_oid = resolve_symbol(oid)
        while True:
            response = await self.session.agetbulk(query_oid, max_repetitions=max_repetitions)
            if not response:
                break
            for oid, value in response:
                if not start_oid.is_a_prefix_of(oid):
                    return results
                query_oid = oid
                results.append(MibObject(oid, value))
        return results

    async def sparsewalk(self, *variables: Sequence[str], max_repetitions: int = 10) -> SparseWalkResponse:
        """Bulkwalks and returns a "sparse" table.

        A sparse walk is just a walk operation that returns selected columns of table (or, from multiple tables that
        augment each other).

        Example usage:
            >>> snmp = SNMP(...)
            >>> snmp.sparsewalk(("IF-MIB", "ifName"), ("IF-MIB", "ifAlias"))
            {OID('.1'): {"ifname": "1", "ifAlias": "uplink"},
             OID('.2'): {"ifName": "2", "ifAlias": "next-sw.example.org"}}
        """
        # See section 4.2.3 of RFC 3416 for reference.  This method does not support
        # non-repeaters values.
        query_objects = roots = [resolve_symbol(symbol) for symbol in variables]
        results: dict[OID, dict[str, Any]] = defaultdict(dict)

        while True:
            query_objects = await self._sparsewalk_iteration(roots, query_objects, results, max_repetitions)
            if not query_objects:
                break  # Nothing left to query
        return dict(results)

    async def _sparsewalk_iteration(
        self, roots: list[OID], query_objects: list[OID], results: dict[OID, dict[str, Any]], max_repetitions: int
    ) -> Optional[list[OID]]:
        """Performs a single iteration of a sparsewalk operation, updating the results dict with the response values.
        Returns the next set of OIDs to query.
        """
        var_binds = await self.session.agetbulk(*query_objects, max_repetitions=max_repetitions)
        if not var_binds:
            return None

        def is_end_of_scope(root: OID, oid: OID, value: Any) -> bool:
            return not root.is_a_prefix_of(oid) or value == EndOfMibView

        # Integrate response values into result dict by processing in chunks of
        # query count. If we want to support non-repeaters, we need to adjust this.
        query_count = len(query_objects)
        response_chunk = (var_binds[i : i + query_count] for i in range(0, len(var_binds), query_count))
        discards = set()
        for chunk in response_chunk:
            for root, query, response in zip(roots, query_objects, chunk):
                oid, value = response
                if is_end_of_scope(root, oid, value):
                    discards.add(oid)
                    continue

                ident, value = _convert_snmp_variable(response)
                results[ident.index][ident.object] = value

        # Prepare next query based on the contents of the last chunk
        query_objects = [oid for oid, _ in chunk if oid not in discards]
        return query_objects

    def is_in_scope(self, entry: MibObject, oid: Tuple[str, str]):
        """Returns if the given MibObject is within the subtree defined by the given OID"""
        root = resolve_symbol(oid)
        return root.is_a_prefix_of(entry.oid)

    async def subtree_is_supported(self, *oid: str) -> bool:
        """Returns if the device has an entry for at least one object within the subtree of the given OID"""
        entry = await self.getnext(*oid)
        return entry and self.is_in_scope(entry=entry, oid=oid)

    @staticmethod
    def _var_bind_to_mibobject(var_bind: tuple[OID, Any]) -> MibObject:
        oid, value = var_bind
        return MibObject(oid=oid, value=value)

    @property
    def snmp_version(self) -> str:
        """Returns the preferred SNMP version of this device as a string"""
        return "v2c" if self.device.hcounters else "v1"


def _convert_snmp_variable(variable: SNMPVariable) -> SNMPVarBind:
    """Converts a netsnmp-cffi  SNMPVariable to an Identifier/value pair.

    We don't want to use the netsnmp-cffi types outside of this module, so we convert them to our own types.
    """
    mib, obj, _rest = _split_symbol(variable.symbolic_name)
    # Net-SNMP does a symbolic breakdown of the full OID, so we need to reassemble the bits we care about:
    prefix = netsnmp.symbol_to_oid(f"{mib}::{obj}")
    suffix = variable.oid.strip_prefix(prefix)

    if variable.enum_value is not None:
        value = variable.enum_value
    elif variable.textual_convention == "DisplayString":
        value = variable.value.decode("utf-8")
    else:
        value = variable.value

    return Identifier(mib, obj, suffix), value


def _split_symbol(symbol: str) -> Tuple[str, str, str]:
    """Splits a MIB symbol string into its parts"""
    parts = symbol.split("::", maxsplit=1)
    if len(parts) == 2:
        mib, parts = parts
    else:
        mib = ""
    if "." in parts:
        obj, row_index = parts.split(".", maxsplit=1)
    else:
        obj = parts
        row_index = ""
    return mib, obj, row_index


def mib_value_to_python(value: Any) -> Any:
    """Translator of raw MIB object values to plainer Python objects.

    This is useful in the PySNMP backend, but the translations have already taken
    place in the netsnmp-cffi backend, so this is a no-op that exists only for
    compatibility.
    """
    return value


def resolve_symbol(*symbol: ObjectIdentifier) -> OID:
    """Resolves a symbolic MIB object to an OID"""
    try:
        return symbol_to_oid(*symbol)
    except ValueError:
        # Translate the library's lookup error to Zino's expected exception
        raise MibNotFoundError(symbol)
