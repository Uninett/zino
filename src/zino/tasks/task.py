from abc import ABC, abstractmethod

from zino.config.models import PollDevice
from zino.state import ZinoState


class Task(ABC):
    def __init__(self, device: PollDevice, state: ZinoState):
        self.device = device
        self.state = state

    @abstractmethod
    async def run(self):
        """Runs job asynchronously"""
