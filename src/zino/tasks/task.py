from abc import ABC, abstractmethod

from zino.config.models import PollDevice


class Task(ABC):
    def __init__(self, device: PollDevice):
        self.device = device

    @abstractmethod
    async def run(self):
        """Runs job asynchronously"""
