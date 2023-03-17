from abc import ABC, abstractmethod

from zino.config.models import PollDevice


class Job(ABC):
    @classmethod
    @abstractmethod
    async def run_job(cls, device: PollDevice):
        """Runs job asynchronously"""
