from datetime import timedelta

import pytest

from zino.statemodels import ReachabilityEvent, ReachabilityState
from zino.tasks.errors import DeviceUnreachableError
from zino.time import now


class TestReachableTask:

    async def test_run_should_not_create_event_if_device_is_reachable(self, reachable_task):
        task = reachable_task
        assert (await task.run()) is None
        event = task.state.events.get(task.device.name, None, ReachabilityEvent)
        assert not event

    async def test_run_should_create_event_if_device_is_unreachable(self, unreachable_task):
        task = unreachable_task
        with pytest.raises(DeviceUnreachableError):
            await task.run()
        event = task.state.events.get(task.device.name, None, ReachabilityEvent)
        assert event

    async def test_run_should_start_extra_job_if_device_is_unreachable(self, unreachable_task):
        with pytest.raises(DeviceUnreachableError):
            await unreachable_task.run()
        assert unreachable_task._extra_job_is_running()

    async def test_run_should_not_start_extra_job_if_device_is_reachable(self, reachable_task):
        task = reachable_task
        assert (await task.run()) is None
        assert not task._extra_job_is_running()

    async def test_run_should_update_event_to_reachable_when_device_is_reachable(self, reachable_task):
        task = reachable_task
        event = task.state.events.create_event(task.device.name, None, ReachabilityEvent)
        event.reachability = ReachabilityState.NORESPONSE
        event.lasttrans = now() - timedelta(minutes=5)
        task.state.events.commit(event)

        assert (await task.run()) is None
        updated_event = task.state.events[event.id]
        assert updated_event.reachability == ReachabilityState.REACHABLE

    async def test_run_should_update_event_to_noresponse_when_device_is_unreachable(self, unreachable_task):
        task = unreachable_task
        event = task.state.events.create_event(task.device.name, None, ReachabilityEvent)
        event.reachability = ReachabilityState.REACHABLE
        task.state.events.commit(event)

        with pytest.raises(DeviceUnreachableError):
            await task.run()
        updated_event = task.state.events[event.id]
        assert updated_event.reachability == ReachabilityState.NORESPONSE

    async def test_run_extra_job_should_update_event_to_reachable_when_device_is_reachable(self, reachable_task):
        task = reachable_task
        event = task.state.events.create_event(task.device.name, None, ReachabilityEvent)
        event.reachability = ReachabilityState.NORESPONSE
        event.lasttrans = now() - timedelta(minutes=5)
        task.state.events.commit(event)

        assert (await task._run_extra_job()) is None
        updated_event = task.state.events[event.id]
        assert updated_event.reachability == ReachabilityState.REACHABLE

    async def test_run_extra_job_should_not_update_event_when_device_is_unreachable(self, unreachable_task):
        task = unreachable_task
        event = task.state.events.create_event(task.device.name, None, ReachabilityEvent)
        event.reachability = ReachabilityState.NORESPONSE
        assert (await task._run_extra_job()) is None
        assert event.reachability == ReachabilityState.NORESPONSE

    @pytest.mark.asyncio
    async def test_when_event_is_new_it_should_set_lasttrans(self, unreachable_task):
        task = unreachable_task
        with pytest.raises(DeviceUnreachableError):
            await task.run()
        event = task.state.events.get(task.device.name, None, ReachabilityEvent)
        assert event.lasttrans

    @pytest.mark.asyncio
    async def test_when_event_transitions_from_no_response_to_reachable_it_should_update_lasttrans(
        self, reachable_task
    ):
        task = reachable_task
        initial_lasttrans = now() - timedelta(minutes=5)

        event = task.state.events.create_event(task.device.name, None, ReachabilityEvent)
        event.reachability = ReachabilityState.NORESPONSE
        event.lasttrans = initial_lasttrans
        task.state.events.commit(event)

        assert (await task.run()) is None
        updated_event = task.state.events[event.id]
        assert updated_event.reachability == ReachabilityState.REACHABLE
        assert updated_event.lasttrans > initial_lasttrans

    @pytest.mark.asyncio
    async def test_when_event_transitions_from_reachable_to_no_response_it_should_update_lasttrans(
        self, unreachable_task
    ):
        task = unreachable_task
        initial_lasttrans = now() - timedelta(minutes=5)

        event = task.state.events.create_event(task.device.name, None, ReachabilityEvent)
        event.reachability = ReachabilityState.REACHABLE
        event.lasttrans = initial_lasttrans
        task.state.events.commit(event)

        with pytest.raises(DeviceUnreachableError):
            await task.run()
        updated_event = task.state.events[event.id]
        assert updated_event.reachability == ReachabilityState.NORESPONSE
        assert updated_event.lasttrans > initial_lasttrans

    @pytest.mark.asyncio
    async def test_when_event_transitions_from_no_response_to_reachable_it_should_update_ac_down(self, reachable_task):
        task = reachable_task
        initial_ac_down = timedelta(0)
        initial_lasttrans = now() - timedelta(minutes=5)

        event = task.state.events.create_event(task.device.name, None, ReachabilityEvent)
        event.reachability = ReachabilityState.NORESPONSE
        event.ac_down = initial_ac_down
        event.lasttrans = initial_lasttrans
        task.state.events.commit(event)

        assert (await task.run()) is None
        updated_event = task.state.events[event.id]
        assert updated_event.reachability == ReachabilityState.REACHABLE
        assert updated_event.ac_down > initial_ac_down
