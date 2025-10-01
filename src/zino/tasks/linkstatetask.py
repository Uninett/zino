import datetime
import logging
import re
from dataclasses import dataclass
from typing import Any

from zino.oid import OID
from zino.scheduler import get_scheduler
from zino.snmp.base import SparseWalkResponse
from zino.statemodels import InterfaceState, Port, PortStateEvent
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

    sysuptime: int = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scheduler = get_scheduler()
        self._make_events_for_new_interfaces = self.config.event.make_events_for_new_interfaces

    async def run(self):
        poll_list = [("IF-MIB", column) for column in BASE_POLL_LIST]
        attrs = await self.snmp.sparsewalk(*poll_list)
        self.sysuptime = await self._get_uptime()
        self.device_state.set_boot_time_from_uptime(self.sysuptime)
        _logger.debug("%s ifattrs: %r", self.device.name, attrs)

        self._update_interfaces(attrs)

    async def poll_single_interface(self, ifindex: int):
        """Polls and updates a single interface.

        This is most often run outside a job context, and must therefore take care of SNMP resource management.
        """
        prev_ifindex = ifindex - 1
        poll_list = [
            ("IF-MIB", column, str(prev_ifindex)) if prev_ifindex else ("IF-MIB", column) for column in BASE_POLL_LIST
        ]
        try:
            with self.snmp as snmp:
                result = await snmp.getnext2(*poll_list)
                self.sysuptime = await self._get_uptime()
        except TimeoutError:
            _logger.error("%s: timed out polling single interface %s", self.device.name, ifindex)
            return
        self.device_state.set_boot_time_from_uptime(self.sysuptime)
        _logger.debug("poll_single_interface %s result: %r", self.device.name, result)

        assert all(ident.index == OID(f".{ifindex}") for ident, value in result)
        row = {ident.object: value for ident, value in result}

        self._update_single_interface(row)

    def _update_interfaces(self, new_attrs: SparseWalkResponse):
        for index, row in new_attrs.items():
            try:
                self._update_single_interface(row)
            except CollectedInterfaceDataIsNotSaneError as error:
                _logger.error(error)

    def _update_single_interface(self, row: dict[str, Any]):
        data = BaseInterfaceRow(*(row.get(attr) for attr in BASE_POLL_LIST))
        if not data.is_sane():
            raise CollectedInterfaceDataIsNotSaneError(self.device.name, data)

        port = self._get_or_create_port(data.index)
        port.ifdescr = data.descr
        self._update_ifalias(port, data)

        if not self._is_interface_watched(data):
            return

        self._update_state(data, port, row)

    def _update_state(self, data: BaseInterfaceRow, port: Port, row: dict[str, Any]):
        for attr in ("ifAdminStatus", "ifOperStatus"):
            if not row.get(attr):
                raise MissingInterfaceTableData(self.device.name, data.index, attr)

        state = f"admin{data.admin_status.capitalize()}"
        if not port.state and self._make_events_for_new_interfaces:
            # This is the first time we see this port
            if data.oper_status != "up" and state != "adminDown":
                port.state = InterfaceState.UNKNOWN
        if state == "adminUp":
            state = data.oper_status
        state = InterfaceState(state)
        if port.state and port.state != state:
            self._make_or_update_state_event(port, state, data.last_change)
        port.state = state

    def _make_or_update_state_event(self, port: Port, new_state: InterfaceState, last_change: int):
        event = self.state.events.get_or_create_event(self.device.name, port.ifindex, PortStateEvent)

        event.portstate = new_state
        event.port = port.ifdescr
        event.ifindex = port.ifindex
        event.polladdr = self.device.address
        event.priority = self.device.priority
        event.descr = port.ifalias

        uptime = self.sysuptime or last_change
        event_time = datetime.datetime.now() - datetime.timedelta(seconds=(uptime - last_change) / 100)

        log = (
            f'{event.router}: port "{port.ifdescr}" ix {port.ifindex} ({port.ifalias}) '
            f"changed state from {port.state} to {new_state} on {event_time}"
        )
        _logger.info(log)
        event.add_log(log)
        self.state.events.commit(event)

        self.schedule_verification_of_single_port(port.ifindex)

    def schedule_verification_of_single_port(
        self, ifindex: int, deadline: datetime.timedelta = datetime.timedelta(minutes=2), reason: str = "verify"
    ):
        """Schedules a verification of a single port at a given time in the future"""
        verification_time = datetime.datetime.now() + deadline
        job_name = f"{self.device.name}-{reason}-{ifindex}-state"
        self._scheduler.add_job(
            func=self.poll_single_interface,
            args=(ifindex,),
            trigger="date",
            run_date=verification_time,
            name=job_name,
        )

    def _get_or_create_port(self, ifindex: int):
        ports = self.device_state.ports
        if ifindex not in ports:
            ports[ifindex] = Port(ifindex=ifindex)
        return ports[ifindex]

    def _is_interface_watched(self, data: BaseInterfaceRow):
        # If watch pattern exists, only watch matching interfaces
        if self.device.watchpat and not re.search(self.device.watchpat, data.descr):
            _logger.debug("%s intf %s not watched", self.device.name, data.descr)
            return False

        # If ignore pattern exists, ignore matching interfaces
        if self.device.ignorepat and re.search(self.device.ignorepat, data.descr):
            _logger.debug("%s intf %s ignored", self.device.name, data.descr)
            return False

        return True

    def _update_ifalias(self, port: Port, data: BaseInterfaceRow):
        new = port.ifalias is None
        change = data.alias != port.ifalias

        if change:
            if not new:
                _logger.info(
                    "%s: changing desc for %s from %r to %r", self.device.name, data.index, port.ifalias, data.alias
                )
            elif data.alias:
                _logger.info("%s: setting desc for %r to %r", self.device.name, data.index, data.alias)
            port.ifalias = data.alias


class MissingInterfaceTableData(Exception):
    def __init__(self, router, port, variable):
        super().__init__(f"No {variable} from {router} for port {port}")


class CollectedInterfaceDataIsNotSaneError(Exception):
    def __init__(self, device: str, interface: BaseInterfaceRow):
        self.device = device
        self.interface = interface
        super().__init__(f"Collected interface data from {device} is not sane enough to process: {interface!r}")
