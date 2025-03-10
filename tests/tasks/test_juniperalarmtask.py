import logging

import pytest

from zino.config.models import PollDevice
from zino.events import AlarmEvent
from zino.state import ZinoState
from zino.tasks.juniperalarmtask import JuniperAlarmTask


class TestJuniperalarmTask:

    async def test_task_runs_without_errors(self, juniper_alarm_task):
        assert (await juniper_alarm_task.run()) is None

    async def test_task_does_nothing_for_non_juniper_device(self, juniper_alarm_task):
        task = juniper_alarm_task
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 11

        await task.run()

        assert device_state.alarms is None

    async def test_task_does_nothing_for_no_result(self, caplog, snmp_test_port):
        device = PollDevice(
            name="buick.lab.example.org",
            address="127.0.0.1",
            community="cisco-bgp",  # Use some non juniper router
            port=snmp_test_port,
        )
        state = ZinoState()
        task = JuniperAlarmTask(device, state)
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 2636

        with caplog.at_level(logging.DEBUG):
            await task.run()

        assert device_state.alarms is None
        assert (
            f"Device {task.device.name} returns alarm count not of type int. Yellow alarm count: type <class 'str'>. Red alarm count: type <class 'str'>."
            not in caplog.text
        )

    async def test_task_logs_error_for_non_int_result(self, caplog, snmp_test_port):
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
        with caplog.at_level(logging.DEBUG):
            await task.run()

        assert device_state.alarms is None
        assert (
            f"Device {task.device.name} returns alarm count not of type int. Yellow alarm count: type <class 'int'>. Red alarm count: type <class 'str'>."
            in caplog.text
        ) or (
            f"Device {task.device.name} returns alarm count not of type int. Yellow alarm count: type <class 'int'>. Red alarm count: type <class 'bytes'>."
            in caplog.text
        )
        assert ("Yellow alarm count: value 0. Red alarm count: value 'buick'." in caplog.text) or (
            "Yellow alarm count: value 0. Red alarm count: value b'buick'." in caplog.text
        )

    async def test_task_saves_alarm_count_in_device_state(self, juniper_alarm_task):
        task = juniper_alarm_task
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 2636

        await task.run()

        assert device_state.alarms
        assert device_state.alarms["yellow"] == 1
        assert device_state.alarms["red"] == 2

    async def test_task_overrides_alarm_count_in_device_state(self, juniper_alarm_task):
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

    async def test_task_creates_both_alarm_events_on_both_counts_changed(self, juniper_alarm_task):
        task = juniper_alarm_task
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 2636

        await task.run()

        yellow_event = task.state.events.get(device_name=task.device.name, subindex="yellow", event_class=AlarmEvent)
        red_event = task.state.events.get(device_name=task.device.name, subindex="red", event_class=AlarmEvent)

        assert yellow_event
        assert red_event
        assert yellow_event.alarm_count == 1
        assert red_event.alarm_count == 2

    async def test_task_creates_one_alarm_event_on_one_count_changed(self, juniper_alarm_task):
        task = juniper_alarm_task
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 2636
        device_state.alarms = {
            "yellow": 1,
            "red": 0,
        }

        await task.run()

        yellow_event = task.state.events.get(device_name=task.device.name, subindex="yellow", event_class=AlarmEvent)
        red_event = task.state.events.get(device_name=task.device.name, subindex="red", event_class=AlarmEvent)

        assert not yellow_event
        assert red_event
        assert red_event.alarm_count == 2

    async def test_task_creates_event_with_correct_log_on_initial_run(self, juniper_alarm_task):
        task = juniper_alarm_task
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 2636
        device_state.alarms = {
            "yellow": 1,
            "red": 0,
        }

        await task.run()

        red_event = task.state.events.get(device_name=task.device.name, subindex="red", event_class=AlarmEvent)

        assert red_event.log
        log_messages = [log_entry.message for log_entry in red_event.log]
        assert f"{juniper_alarm_task.device.name} red alarms went from 0 to 2" in log_messages

    async def test_task_updates_alarm_events(self, juniper_alarm_task):
        task = juniper_alarm_task
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 2636
        yellow_event = task.state.events.get_or_create_event(
            device_name=task.device.name, subindex="yellow", event_class=AlarmEvent
        )
        yellow_event.alarm_type = "yellow"
        yellow_event.alarm_count = 2
        task.state.events.commit(yellow_event)
        red_event = task.state.events.get_or_create_event(
            device_name=task.device.name, subindex="red", event_class=AlarmEvent
        )
        red_event.alarm_type = "red"
        red_event.alarm_count = 3
        task.state.events.commit(red_event)

        await task.run()

        new_yellow_event, new_red_event = task.state.events[yellow_event.id], task.state.events[red_event.id]
        assert new_yellow_event.alarm_count == 1
        assert new_red_event.alarm_count == 2

    async def test_task_does_not_create_alarm_events_on_unchanged_alarm_count(self, juniper_alarm_task):
        task = juniper_alarm_task
        device_state = task.state.devices.get(device_name=task.device.name)
        device_state.enterprise_id = 2636
        device_state.alarms = {
            "yellow": 1,
            "red": 2,
        }

        await task.run()

        yellow_event = task.state.events.get(device_name=task.device.name, subindex="yellow", event_class=AlarmEvent)
        red_event = task.state.events.get(device_name=task.device.name, subindex="red", event_class=AlarmEvent)

        assert not yellow_event
        assert not red_event

    async def test_task_does_not_create_alarm_events_on_alarm_count_zero_on_first_run(self, snmp_test_port):
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

        yellow_event = task.state.events.get(device_name=task.device.name, subindex="yellow", event_class=AlarmEvent)
        red_event = task.state.events.get(device_name=task.device.name, subindex="red", event_class=AlarmEvent)

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
