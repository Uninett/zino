import logging

from zino.snmp import get_snmp_session
from zino.tasks.errors import DeviceUnreachableError

_log = logging.getLogger(__name__)


async def run_all_tasks(device, state, config):
    try:
        with get_snmp_session(device):
            await run_registered_tasks(device, state, config)
    except DeviceUnreachableError:
        _log.debug(f"Device {device.name} could not be reached. Any remaining tasks have been cancelled.")


async def run_registered_tasks(device, state, config):
    for task_class in get_registered_tasks():
        task = task_class(device, state, config)
        try:
            await task.run()
        except TimeoutError:
            _log.error(
                "%s: %s raised an unexpected TimeoutError mid-run, cancelling remaining tasks in this run",
                device.name,
                task_class.__name__,
            )
            return


def get_registered_tasks():
    from zino.tasks.addrs import AddressMapTask
    from zino.tasks.bfdtask import BFDTask
    from zino.tasks.bgpstatemonitortask import BGPStateMonitorTask
    from zino.tasks.juniperalarmtask import JuniperAlarmTask
    from zino.tasks.linkstatetask import LinkStateTask
    from zino.tasks.reachabletask import ReachableTask
    from zino.tasks.vendor import VendorTask

    return [ReachableTask, VendorTask, AddressMapTask, LinkStateTask, BFDTask, BGPStateMonitorTask, JuniperAlarmTask]
