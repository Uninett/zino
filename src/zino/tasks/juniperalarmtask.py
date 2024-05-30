import logging

from zino.snmp import NoSuchNameError
from zino.statemodels import AlarmEvent, AlarmType
from zino.tasks.task import Task

_logger = logging.getLogger(__name__)


class JuniperAlarmTask(Task):
    """Checks yellow and red alarm count for juniper device."""

    async def run(self):
        if not self.device_state.is_juniper:
            return

        try:
            yellow_alarm_count, red_alarm_count = await self._get_juniper_alarms()
        except (TypeError, NoSuchNameError):
            return

        if not self.device_state.alarms:
            self.device_state.alarms = {
                "yellow": 0,
                "red": 0,
            }

        if self.device_state.alarms["yellow"] != yellow_alarm_count:
            self.device_state.alarms["yellow"] = yellow_alarm_count
            self.create_alarm_event(color="yellow", alarm_count=yellow_alarm_count)

        if self.device_state.alarms["red"] != red_alarm_count:
            self.device_state.alarms["red"] = red_alarm_count
            self.create_alarm_event(color="red", alarm_count=red_alarm_count)

    async def _get_juniper_alarms(self):
        yellow_alarm_count = await self.snmp.get("JUNIPER-ALARM-MIB", "jnxYellowAlarmCount", 0)
        red_alarm_count = await self.snmp.get("JUNIPER-ALARM-MIB", "jnxRedAlarmCount", 0)
        if yellow_alarm_count:
            yellow_alarm_count = yellow_alarm_count.value
        if red_alarm_count:
            red_alarm_count = red_alarm_count.value

        if not isinstance(yellow_alarm_count, int) or not isinstance(red_alarm_count, int):
            _logger.error(
                "Device %s returns alarm count not of type int. "
                "Yellow alarm count: type %s. Red alarm count: type %s.",
                self.device.name,
                type(yellow_alarm_count),
                type(red_alarm_count),
            )
            _logger.debug(
                "Yellow alarm count: value %r. Red alarm count: value %r.",
                yellow_alarm_count,
                red_alarm_count,
            )
            raise TypeError

        return yellow_alarm_count, red_alarm_count

    def create_alarm_event(self, color: AlarmType, alarm_count: int):
        alarm_event = self.state.events.get_or_create_event(
            device_name=self.device.name,
            subindex=color,
            event_class=AlarmEvent,
        )

        old_alarm_count = alarm_event.alarm_count
        log = f"alarms went from {old_alarm_count} to {alarm_count}"
        alarm_event.alarm_type = color
        alarm_event.alarm_count = alarm_count
        alarm_event.add_log(f"{self.device.name} {color} {log}")
        alarm_event.polladdr = self.device.address
        alarm_event.priority = self.device.priority
        alarm_event.lastevent = log
        self.state.events.commit(alarm_event)
