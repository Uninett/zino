import pytest

from zino.config.models import PollDevice
from zino.events import AlarmEvent
from zino.state import ZinoState
from zino.tasks.juniperalarmtask import JuniperAlarmTask


class TestJuniperalarmTask:
    @pytest.mark.asyncio
    async def test_task_runs_without_errors(self, snmpsim, juniper_alarm_task):
        assert (await juniper_alarm_task.run()) is None

    @pytest.mark.asyncio
    async def test_task_does_nothing_for_non_juniper_device(self, snmpsim, juniper_alarm_task):
        task = juniper_alarm_task
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 11

        await task.run()

        assert device_state.alarms is None

    @pytest.mark.asyncio
    async def test_task_does_nothing_for_non_int_result(self, snmpsim, snmp_test_port):
        device = PollDevice(
            name="buick.lab.example.org",
            address="127.0.0.1",
            community="juniper-alarm-wrong",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = JuniperAlarmTask(device, state)
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 2636
        await task.run()

        assert device_state.alarms is None

    @pytest.mark.asyncio
    async def test_task_saves_alarm_count_in_device_state(self, snmpsim, juniper_alarm_task):
        task = juniper_alarm_task
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 2636

        await task.run()

        assert device_state.alarms
        assert device_state.alarms["yellow"] == 1
        assert device_state.alarms["red"] == 2

    @pytest.mark.asyncio
    async def test_task_overrides_alarm_count_in_device_state(self, snmpsim, juniper_alarm_task):
        task = juniper_alarm_task
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 2636
        device_state.alarms = {
            "yellow": 2,
            "red": 3,
        }

        await task.run()

        assert device_state.alarms["yellow"] == 1
        assert device_state.alarms["red"] == 2

    @pytest.mark.asyncio
    async def test_task_creates_both_alarm_events_on_both_counts_changed(self, snmpsim, juniper_alarm_task):
        task = juniper_alarm_task
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 2636

        await task.run()

        yellow_event = task.state.events.get(device_name=task.device.name, port="yellow", event_class=AlarmEvent)
        red_event = task.state.events.get(device_name=task.device.name, port="red", event_class=AlarmEvent)

        assert yellow_event
        assert red_event
        assert yellow_event.alarm_count == 1
        assert red_event.alarm_count == 2

    @pytest.mark.asyncio
    async def test_task_creates_one_alarm_event_on_one_count_changed(self, snmpsim, juniper_alarm_task):
        task = juniper_alarm_task
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 2636
        device_state.alarms = {
            "yellow": 0,
            "red": 0,
        }

        await task.run()

        yellow_event = task.state.events.get(device_name=task.device.name, port="yellow", event_class=AlarmEvent)
        red_event = task.state.events.get(device_name=task.device.name, port="red", event_class=AlarmEvent)

        assert not yellow_event
        assert red_event
        assert red_event.alarm_count == 2

    @pytest.mark.asyncio
    async def test_task_updates_alarm_events(self, snmpsim, juniper_alarm_task):
        task = juniper_alarm_task
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 2636
        yellow_event, _ = task.state.events.get_or_create_event(
            device_name=task.device.name, port="yellow", event_class=AlarmEvent
        )
        yellow_event.alarm_count = 2
        red_event, _ = task.state.events.get_or_create_event(
            device_name=task.device.name, port="red", event_class=AlarmEvent
        )
        red_event.alarm_count = 3

        await task.run()

        assert yellow_event.alarm_count == 1
        assert red_event.alarm_count == 2

    @pytest.mark.asyncio
    async def test_task_does_not_create_alarm_events_on_unchanged_alarm_count(self, snmpsim, juniper_alarm_task):
        task = juniper_alarm_task
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 2636
        device_state.alarms = {
            "yellow": 1,
            "red": 2,
        }

        await task.run()

        yellow_event = task.state.events.get(device_name=task.device.name, port="yellow", event_class=AlarmEvent)
        red_event = task.state.events.get(device_name=task.device.name, port="red", event_class=AlarmEvent)

        assert not yellow_event
        assert not red_event

    @pytest.mark.asyncio
    async def test_task_does_not_create_alarm_events_on_alarm_count_zero_on_first_run(self, snmpsim, snmp_test_port):
        device = PollDevice(
            name="buick.lab.example.org",
            address="127.0.0.1",
            community="juniper-alarm-zero",
            port=snmp_test_port,
        )
        state = ZinoState()
        task = JuniperAlarmTask(device, state)
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 2636
        await task.run()

        yellow_event = task.state.events.get(device_name=task.device.name, port="yellow", event_class=AlarmEvent)
        red_event = task.state.events.get(device_name=task.device.name, port="red", event_class=AlarmEvent)

        assert not yellow_event
        assert not red_event


@pytest.fixture()
def juniper_alarm_task(snmpsim, snmp_test_port):
    device = PollDevice(
        name="buick.lab.example.org",
        address="127.0.0.1",
        community="juniper-alarm",
        port=snmp_test_port,
    )
    state = ZinoState()
    task = JuniperAlarmTask(device, state)
    yield task
