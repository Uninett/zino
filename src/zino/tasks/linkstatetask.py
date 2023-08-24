import logging
import re
from dataclasses import dataclass
from typing import Any

from zino.snmp import SNMP, SparseWalkResponse
from zino.statemodels import InterfaceState, Port
from zino.tasks.task import Task

_logger = logging.getLogger(__name__)

BASE_POLL_LIST = ("ifIndex", "ifDescr", "ifAlias", "ifAdminStatus", "ifOperStatus", "ifLastChange")


@dataclass
class BaseInterfaceRow:
    index: int
    descr: str
    alias: str
    admin_status: str
    oper_status: str
    last_change: int

    def is_sane(self) -> bool:
        return bool(self.index and self.descr)


class LinkStateTask(Task):
    """Fetches and stores state information about router ports/links.

    Things Zino 1 does at this point that this implementation ignores:

    1. Zino 1 would fetch and record OLD-CISCO-INTERFACES-MIB::locIfReason, but this isn't very useful for anything
    other than very old equipment.

    2. Zino 1 collects and records interface stacking/layering information from IF-MIB::ifStackTable. It was used to
    deem an interface as either significant or insignificant for making events about.  It was used because Uninett's
    old convention was to set interface descriptions on only the sub-unit of Juniper ports, but this is no longer the
    case: Descriptions are mandated for both physical ports and their sub-units.
    """

    async def run(self):
        snmp = SNMP(self.device)
        poll_list = [("IF-MIB", column) for column in BASE_POLL_LIST]
        attrs = await snmp.sparsewalk(*poll_list)
        _logger.debug("%s ifattrs: %r", self.device.name, attrs)

        self._update_interfaces(attrs)

    def _update_interfaces(self, new_attrs: SparseWalkResponse):
        for index, row in new_attrs.items():
            self._update_single_interface(row)

    def _update_single_interface(self, row: dict[str, Any]):
        data = BaseInterfaceRow(*(row.get(attr) for attr in BASE_POLL_LIST))
        if not data.is_sane():
            return

        # Now ensure we have a state object to record information in
        ports = self.state.devices.get(self.device.name).ports
        if data.index not in ports:
            ports[data.index] = Port(ifindex=data.index)
        port = ports[data.index]
        if not self._is_interface_watched(data):
            return

        port.ifdescr = data.descr

        for attr in ("ifAdminStatus", "ifOperStatus"):
            if not row.get(attr):
                raise MissingInterfaceTableData(self.device.name, data.index, attr)

        state = f"admin{data.admin_status.capitalize()}"
        # A special tweak so that we report ports in oper-down (but admin-up) state first time we see them
        if not port.state and data.oper_status != "up" and state != "adminDown":
            port.state = InterfaceState.UNKNOWN
        if state == "adminUp":
            state = data.oper_status

        state = InterfaceState(state)
        if port.state and port.state != state:
            # TODO make or update event
            # TODO Re-verify state change after 2 minutes
            _logger.info(
                "%s port %s ix %s port changed state from %s to %s",
                self.device.name,
                data.descr,
                data.index,
                port.state,
                state,
            )

        port.state = state

    def _is_interface_watched(self, data: BaseInterfaceRow):
        # If watch pattern exists, only watch matching interfaces
        if self.device.watchpat:
            if not re.match(self.device.watchpat, data.descr):
                _logger.debug("%s intf %s not watched", self.device.name, data.descr)
                return False

        # If ignore pattern exists, ignore matching interfaces
        if self.device.ignorepat:
            if re.match(self.device.ignorepat, data.descr):
                _logger.debug("%s intf %s ignored", self.device.name, data.descr)
                return False

        return True


class MissingInterfaceTableData(Exception):
    def __init__(self, router, port, variable):
        super().__init__(f"No {variable} from {router} for port {port}")
