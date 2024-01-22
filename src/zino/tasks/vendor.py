import logging
from typing import Optional, Tuple

from zino.tasks.task import Task

_logger = logging.getLogger(__name__)
ENTERPRISES = (1, 3, 6, 1, 4, 1)


class VendorTask(Task):
    """Fetches and stores state information about a Device's vendor"""

    async def run(self):
        vendor = await self._get_enterprise_id()
        _logger.debug("%s enterprise id: %r", self.device.name, vendor)

        if self.device_state.enterprise_id != vendor:
            _logger.info(
                "%s changed enterprise id from %s to %s", self.device.name, self.device_state.enterprise_id, vendor
            )
            self.device_state.enterprise_id = vendor

    async def _get_enterprise_id(self) -> Optional[int]:
        sysobjectid = await self._get_sysobjectid()
        # This part can probably be a whole lot prettier if we learned how to utilize PySNMP properly:
        if sysobjectid[: len(ENTERPRISES)] == ENTERPRISES:
            return sysobjectid[len(ENTERPRISES)]

    async def _get_sysobjectid(self) -> Optional[Tuple[int, ...]]:
        result = await self.snmp.get("SNMPv2-MIB", "sysObjectID", 0)
        return result.value
