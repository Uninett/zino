import logging
from ipaddress import ip_address
from typing import Any, List, Optional

from zino.snmp import SNMP
from zino.statemodels import IPAddress
from zino.tasks.task import Task

_logger = logging.getLogger(__name__)


class AddressMapTask(Task):
    """Fetches and stores mappings between router names and router interface addresses in state data.

    These mappings can be used for things like identifying the originating router from SNMP traps that are sent using
    a different source address than the management interface Zino normally talks to.
    """

    async def run(self):
        addresses = await self._get_addrs()
        _logger.debug("found addresses for %s: %r", self.device.name, addresses)
        self._update_address_maps(addresses)

    async def _get_addrs(self) -> set[IPAddress]:
        snmp = SNMP(self.device)
        result = await snmp.bulkwalk("IP-MIB", "ipAdEntAddr")
        addresses = (validate_ipaddr(r.value) for r in result)
        return set(addr for addr in addresses if addr)

    def _update_address_maps(self, addresses: List[IPAddress]):
        state = self.state
        for address in addresses:
            # Here we need a mechanism get gets a list of ignores from config:
            # if ignoreAddress(address):
            #     continue
            if address not in state.addresses:
                _logger.info("%s adds address %s", self.device.name, address)
            elif state.addresses[address] != self.device.name:
                _logger.info("Home of %s changed from %s to %s", address, state.addresses[address], self.device.name)

            state.addresses[address] = self.device.name

        self.device_state.addresses = addresses

        missing_addresses = set(
            address
            for address, router in state.addresses.items()
            if router == self.device.name and address not in addresses
        )
        if missing_addresses:
            _logger.info("%s no longer has these addresses: %r", self.device.name, missing_addresses)
            for address in missing_addresses:
                del state.addresses[address]


def validate_ipaddr(address: Any) -> Optional[IPAddress]:
    """Converts and returns address as a IPv4Address or IPv6Address object.  Returns None if the address is invalid."""
    try:
        return ip_address(address)
    except ValueError:
        return None
