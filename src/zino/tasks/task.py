from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from zino.config.models import PollDevice
from zino.snmp import SNMP

if TYPE_CHECKING:
    from zino.state import ZinoState

from zino.statemodels import DeviceState


class Task(ABC):
    def __init__(self, device: PollDevice, state: ZinoState):
        self.device = device
        self.state = state
        self.snmp = SNMP(device=device)

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
