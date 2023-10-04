from unittest.mock import patch

import pytest

from zino.config.models import PollDevice
from zino.state import ZinoState
from zino.statemodels import EventState, ReachabilityEvent, ReachabilityState
from zino.tasks.reachabletask import ReachableTask


@pytest.fixture()
def reachable_task(snmpsim, snmp_test_port):
    device = PollDevice(name="buick.lab.example.org", address="127.0.0.1", port=snmp_test_port)
    state = ZinoState()
    task = ReachableTask(device, state)
    yield task
    task._deschedule_extra_job()


@pytest.fixture()
def unreachable_task():
    device = PollDevice(name="nonexist", address="127.0.0.1", community="invalid", port=666, timeout=1)
    state = ZinoState()
    task = ReachableTask(device, state)
    with patch("zino.tasks.reachabletask.SNMP.get") as get_mock:
        get_mock.side_effect = TimeoutError
        yield task
    task._deschedule_extra_job()


class TestReachableTask:
    @pytest.mark.asyncio
    async def test_run_should_not_create_event_if_device_is_reachable(self, reachable_task):
        task = reachable_task
        assert (await task.run()) is None
        event = task.state.events.get(task.device.name, None, ReachabilityEvent)
        assert not event

    @pytest.mark.asyncio
    async def test_run_should_create_event_if_device_is_unreachable(self, unreachable_task):
        task = unreachable_task
        assert (await unreachable_task.run()) is None
        event = task.state.events.get(task.device.name, None, ReachabilityEvent)
        assert event

    @pytest.mark.asyncio
    async def test_run_should_start_extra_job_if_device_is_unreachable(self, unreachable_task):
        assert (await unreachable_task.run()) is None
        assert unreachable_task._extra_job_is_running()

    @pytest.mark.asyncio
    async def test_run_should_not_start_extra_job_if_device_is_reachable(self, reachable_task):
        task = reachable_task
        assert (await task.run()) is None
        assert not task._extra_job_is_running()

    @pytest.mark.asyncio
    async def test_run_should_update_event_to_reachable_when_device_is_reachable(self, reachable_task):
        task = reachable_task
        event = task.state.events.create_event(task.device.name, None, ReachabilityEvent)
        event.state = EventState.OPEN
        event.reachability = ReachabilityState.NORESPONSE
        assert (await task.run()) is None
        assert event.reachability == ReachabilityState.REACHABLE

    @pytest.mark.asyncio
    async def test_run_should_update_event_to_noresponse_when_device_is_unreachable(self, unreachable_task):
        task = unreachable_task
        event = task.state.events.create_event(task.device.name, None, ReachabilityEvent)
        event.state = EventState.OPEN
        event.reachability = ReachabilityState.REACHABLE
        assert (await task.run()) is None
        assert event.reachability == ReachabilityState.NORESPONSE

    @pytest.mark.asyncio
    async def test_run_extra_job_should_update_event_to_reachable_when_device_is_reachable(self, reachable_task):
        task = reachable_task
        event = task.state.events.create_event(task.device.name, None, ReachabilityEvent)
        event.state = EventState.OPEN
        event.reachability = ReachabilityState.NORESPONSE
        assert (await task._run_extra_job()) is None
        assert event.reachability == ReachabilityState.REACHABLE

    @pytest.mark.asyncio
    async def test_run_extra_job_should_not_update_event_when_device_is_unreachable(self, unreachable_task):
        task = unreachable_task
        event = task.state.events.create_event(task.device.name, None, ReachabilityEvent)
        event.state = EventState.OPEN
        event.reachability = ReachabilityState.NORESPONSE
        assert (await task._run_extra_job()) is None
        assert event.reachability == ReachabilityState.NORESPONSE
