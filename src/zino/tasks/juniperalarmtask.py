import logging
from typing import Literal

from zino.snmp import SNMP
from zino.statemodels import AlarmEvent, EventState
from zino.tasks.task import Task

_logger = logging.getLogger(__name__)


class JuniperAlarmTask(Task):
    """Checks yellow and red alarm count for juniper device."""

    async def run(self):
        device_state = self.state.devices.get(self.device.name)
        if not device_state.is_juniper:
            return

        try:
            yellow_alarm_count, red_alarm_count = await self._get_juniper_alarms()
        except TypeError:
            return

        if not device_state.alarms:
            device_state.alarms = {
                "yellow": 0,
                "red": 0,
            }

        if device_state.alarms["yellow"] != yellow_alarm_count:
            device_state.alarms["yellow"] = yellow_alarm_count
            self.create_alarm_event(color="yellow", alarm_count=yellow_alarm_count)

        if device_state.alarms["red"] != red_alarm_count:
            device_state.alarms["red"] = red_alarm_count
            self.create_alarm_event(color="red", alarm_count=red_alarm_count)

    async def _get_juniper_alarms(self):
        snmp = SNMP(self.device)
        yellow_alarm_count = await snmp.get("JUNIPER-ALARM-MIB", "jnxYellowAlarmCount", 0)
        red_alarm_count = await snmp.get("JUNIPER-ALARM-MIB", "jnxRedAlarmCount", 0)
        if yellow_alarm_count:
            yellow_alarm_count = yellow_alarm_count.value
        if red_alarm_count:
            red_alarm_count = red_alarm_count.value

        if type(yellow_alarm_count) is not int or type(red_alarm_count) is not int:
            _logger.error(
                "Device %s returns alarm count not of type int. "
                "Yellow alarm count: type %s, value %s. "
                "Red alarm count: type %s, value %s.",
                self.device.name,
                type(yellow_alarm_count),
                yellow_alarm_count,
                type(red_alarm_count),
                red_alarm_count,
            )
            raise TypeError

        return yellow_alarm_count, red_alarm_count

    def create_alarm_event(self, color: Literal["yellow", "red"], alarm_count: int):
        alarm_event, created = self.state.events.get_or_create_event(
            device_name=self.device.name,
            port=color,
            event_class=AlarmEvent,
        )
        if created:
            alarm_event.state = EventState.OPEN
            alarm_event.add_history("Change state to Open")

        old_alarm_count = alarm_event.alarm_count
        alarm_event.alarm_count = alarm_count
        alarm_event.add_log(f"{self.device.name} {color} alarms went from {old_alarm_count} to {alarm_count}")
