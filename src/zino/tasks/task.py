from abc import ABC, abstractmethod

from zino.config.models import PollDevice


class Task(ABC):
    @abstractmethod
    async def run_task(cls, device: PollDevice):
        """Runs job asynchronously"""
