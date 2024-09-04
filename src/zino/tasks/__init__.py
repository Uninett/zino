import logging

from zino.config.models import PollDevice
from zino.state import ZinoState
from zino.tasks.errors import DeviceUnreachableError
from zino.utils import log_time_spent

_log = logging.getLogger(__name__)


async def run_all_tasks(device, state):
    try:
        await run_registered_tasks(device, state)
    except DeviceUnreachableError:
        _log.debug(f"Device {device.name} could not be reached. Any remaining tasks have been cancelled.")


@log_time_spent(logger="zino.tasktime", level=logging.INFO, limit=30.0, formatter=lambda args, kwargs: args[0].name)
async def run_registered_tasks(device: PollDevice, state: ZinoState):
    for task_class in get_registered_tasks():
        task = task_class(device, state)
        await task.run()


def get_registered_tasks():
    from zino.tasks.addrs import AddressMapTask
    from zino.tasks.bfdtask import BFDTask
    from zino.tasks.bgpstatemonitortask import BGPStateMonitorTask
    from zino.tasks.juniperalarmtask import JuniperAlarmTask
    from zino.tasks.linkstatetask import LinkStateTask
    from zino.tasks.reachabletask import ReachableTask
    from zino.tasks.vendor import VendorTask

    return [ReachableTask, VendorTask, AddressMapTask, LinkStateTask, BFDTask, BGPStateMonitorTask, JuniperAlarmTask]
