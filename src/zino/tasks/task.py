from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from zino.config.models import Configuration, PollDevice
from zino.snmp import get_snmp_session

if TYPE_CHECKING:
    from zino.state import ZinoState

from zino.statemodels import DeviceState


class Task(ABC):
    def __init__(self, device: PollDevice, state: ZinoState, config: Optional[Configuration] = None):
        self.device = device
        self.state = state
        self.config = config
        self.snmp = get_snmp_session(device=device)

    @abstractmethod
    async def run(self):
        """Runs job asynchronously"""

    async def _get_uptime(self) -> int:
        """Polls and returns the device sysuptime value"""
        response = await self.snmp.get("SNMPv2-MIB", "sysUpTime", 0)
        uptime = response.value
        return uptime

    @property
    def device_state(self) -> DeviceState:
        return self.state.devices.get(self.device.name)
