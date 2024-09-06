import logging
from datetime import timedelta
from ipaddress import IPv4Address

import pytest

from zino.config.models import PollDevice
from zino.state import ZinoState
from zino.statemodels import (
    BGPAdminStatus,
    BGPEvent,
    BGPOperState,
    BGPPeerSession,
    BGPStyle,
)
from zino.tasks.bgpstatemonitortask import BaseBGPRow, BGPStateMonitorTask
from zino.time import now

PEER_ADDRESS = IPv4Address("10.0.0.1")
DEFAULT_REMOTE_AS = 20
DEFAULT_UPTIME = 250


class TestBGPStateMonitorTask:

    @pytest.mark.parametrize("task", ["public", "juniper-bgp", "cisco-bgp", "general-bgp"], indirect=True)
    async def test_task_runs_without_errors(self, task):
        assert (await task.run()) is None

    @pytest.mark.parametrize("task", ["missing-info-bgp"], indirect=True)
    async def test_task_logs_missing_information(self, task, caplog):
        """Tests that the BGP state monitor task logs if necessary information for a BGP device is missing"""
        with caplog.at_level(logging.INFO):
            await task.run()

        assert f"router {task.device.name} misses BGP variables" in caplog.text

    @pytest.mark.parametrize(
        "task", ["general-bgp-external-reset", "cisco-bgp-external-reset", "juniper-bgp-external-reset"], indirect=True
    )
    async def test_external_reset_creates_event(self, task):
        """Tests that an event should be made if a BGP connection to a device has been reset"""
        # set initial state
        task.device_state.bgp_peers = {
            PEER_ADDRESS: BGPPeerSession(uptime=500, admin_status=BGPAdminStatus.STOP, oper_state=BGPOperState.DOWN)
        }
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peers[PEER_ADDRESS].admin_status in [BGPAdminStatus.RUNNING, BGPAdminStatus.START]
        assert task.device_state.bgp_peers[PEER_ADDRESS].oper_state == BGPOperState.ESTABLISHED
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, subindex=PEER_ADDRESS, event_class=BGPEvent)
        assert event
        assert event.admin_status in [BGPAdminStatus.RUNNING, BGPAdminStatus.START]
        assert event.operational_state == BGPOperState.ESTABLISHED
        assert event.remote_address == PEER_ADDRESS
        assert event.remote_as == DEFAULT_REMOTE_AS
        assert event.peer_uptime == DEFAULT_UPTIME

    @pytest.mark.parametrize(
        "task", ["general-bgp-external-reset", "cisco-bgp-external-reset", "juniper-bgp-external-reset"], indirect=True
    )
    async def test_session_up_updates_event(self, task):
        """Tests that the oper down event should be updated if a BGP connection to a device reports that their
        oper_state has changed back to established
        """
        # create admin down event
        event = task.state.events.get_or_create_event(
            device_name=task.device.name, subindex=PEER_ADDRESS, event_class=BGPEvent
        )
        event.operational_state = BGPOperState.DOWN
        event.admin_status = BGPAdminStatus.STOP
        event.remote_address = PEER_ADDRESS
        event.remote_as = DEFAULT_REMOTE_AS
        event.peer_uptime = 0
        task.state.events.commit(event=event)

        await task.run()

        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peers[PEER_ADDRESS].admin_status in [BGPAdminStatus.RUNNING, BGPAdminStatus.START]
        assert task.device_state.bgp_peers[PEER_ADDRESS].oper_state == BGPOperState.ESTABLISHED
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, subindex=PEER_ADDRESS, event_class=BGPEvent)
        assert event
        assert event.admin_status in [BGPAdminStatus.RUNNING, BGPAdminStatus.START]
        assert event.operational_state == BGPOperState.ESTABLISHED
        assert event.remote_address == PEER_ADDRESS
        assert event.remote_as == DEFAULT_REMOTE_AS
        assert event.peer_uptime == DEFAULT_UPTIME

    @pytest.mark.parametrize(
        "task", ["general-bgp-admin-down", "cisco-bgp-admin-down", "juniper-bgp-admin-down"], indirect=True
    )
    async def test_admin_down_creates_event(self, task):
        """Tests that an event should be made if a BGP connection to a device reports that their admin_status has
        changed from start to stop
        """
        # set initial state
        task.device_state.bgp_peers = {
            PEER_ADDRESS: BGPPeerSession(
                uptime=DEFAULT_UPTIME, admin_status=BGPAdminStatus.START, oper_state=BGPOperState.ESTABLISHED
            )
        }
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peers[PEER_ADDRESS].admin_status in [BGPAdminStatus.HALTED, BGPAdminStatus.STOP]
        assert task.device_state.bgp_peers[PEER_ADDRESS].oper_state != BGPOperState.ESTABLISHED
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, subindex=PEER_ADDRESS, event_class=BGPEvent)
        assert event
        assert event.admin_status in [BGPAdminStatus.HALTED, BGPAdminStatus.STOP]
        assert event.operational_state == BGPOperState.DOWN
        assert event.remote_address == PEER_ADDRESS
        assert event.remote_as == DEFAULT_REMOTE_AS
        assert event.peer_uptime == 0

    @pytest.mark.parametrize(
        "task", ["general-bgp-admin-up", "cisco-bgp-admin-up", "juniper-bgp-admin-up"], indirect=True
    )
    async def test_admin_up_creates_event(self, task):
        """Tests that an event should be made if a BGP connection to a device reports that their admin_status has
        changed from stop to start
        """
        # set initial state
        task.device_state.bgp_peers = {
            PEER_ADDRESS: BGPPeerSession(
                uptime=DEFAULT_UPTIME,
                admin_status=BGPAdminStatus.STOP,
                oper_state=BGPOperState.IDLE,
            )
        }
        # create admin down event
        event = task.state.events.get_or_create_event(
            device_name=task.device.name, subindex=PEER_ADDRESS, event_class=BGPEvent
        )
        event.operational_state = BGPOperState.DOWN
        event.admin_status = BGPAdminStatus.STOP
        event.remote_address = PEER_ADDRESS
        event.remote_as = DEFAULT_REMOTE_AS
        event.peer_uptime = 0
        task.state.events.commit(event=event)

        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peers[PEER_ADDRESS].admin_status in [BGPAdminStatus.RUNNING, BGPAdminStatus.START]
        assert task.device_state.bgp_peers[PEER_ADDRESS].oper_state != BGPOperState.ESTABLISHED
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, subindex=PEER_ADDRESS, event_class=BGPEvent)
        assert event
        assert event.admin_status in [BGPAdminStatus.RUNNING, BGPAdminStatus.START]
        assert event.operational_state == BGPOperState.IDLE
        assert event.remote_address == PEER_ADDRESS
        assert event.remote_as == DEFAULT_REMOTE_AS
        assert event.peer_uptime == 0

    @pytest.mark.parametrize(
        "task", ["general-bgp-oper-down", "cisco-bgp-oper-down", "juniper-bgp-oper-down"], indirect=True
    )
    async def test_oper_down_creates_event(self, task):
        """Tests that an event should be made if a BGP connection to a device reports that their oper_state has changed
        from established to something else
        """
        # set initial state
        task.device_state.bgp_peers = {
            PEER_ADDRESS: BGPPeerSession(
                uptime=DEFAULT_UPTIME, admin_status=BGPAdminStatus.START, oper_state=BGPOperState.ESTABLISHED
            )
        }
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peers[PEER_ADDRESS].oper_state != BGPOperState.ESTABLISHED
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, subindex=PEER_ADDRESS, event_class=BGPEvent)
        assert event
        assert event.admin_status in [BGPAdminStatus.RUNNING, BGPAdminStatus.START]
        assert event.operational_state == BGPOperState.DOWN
        assert event.remote_address == PEER_ADDRESS
        assert event.remote_as == DEFAULT_REMOTE_AS
        assert event.peer_uptime == 1000000

    @pytest.mark.parametrize(
        "task", ["general-bgp-oper-down", "cisco-bgp-oper-down", "juniper-bgp-oper-down"], indirect=True
    )
    async def test_oper_down_creates_serializable_event(self, task):
        """Tests that an event created from a BGP state change should be serializable by Pydantic without warnings"""
        # set initial state
        task.device_state.bgp_peers = {
            PEER_ADDRESS: BGPPeerSession(
                uptime=DEFAULT_UPTIME, admin_status=BGPAdminStatus.START, oper_state=BGPOperState.ESTABLISHED
            )
        }
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peers[PEER_ADDRESS].oper_state != BGPOperState.ESTABLISHED
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, subindex=PEER_ADDRESS, event_class=BGPEvent)
        assert event
        assert event.model_dump_json(exclude_none=True, indent=2, warnings="error")

    @pytest.mark.parametrize(
        "task",
        ["general-bgp-oper-down-short", "cisco-bgp-oper-down-short", "juniper-bgp-oper-down-short"],
        indirect=True,
    )
    async def test_oper_down_does_not_create_event_if_uptime_less_than_specified(self, task):
        """Tests that an event should not be made if a BGP connection to a device reports that their oper_state has
        changed from established to something else, but the uptime is less than a specified time
        """
        # set initial state
        if task.device_state.bgp_style == BGPStyle.JUNIPER:
            task.device_state.bgp_peers = {
                PEER_ADDRESS: BGPPeerSession(
                    uptime=DEFAULT_UPTIME, admin_status=BGPAdminStatus.RUNNING, oper_state=BGPOperState.ESTABLISHED
                )
            }
        else:
            task.device_state.bgp_peers = {
                PEER_ADDRESS: BGPPeerSession(
                    uptime=DEFAULT_UPTIME, admin_status=BGPAdminStatus.START, oper_state=BGPOperState.ESTABLISHED
                )
            }
        await task.run()
        # check if state has been updated to reflect state defined in .snmprec
        assert task.device_state.bgp_peers[PEER_ADDRESS].oper_state != BGPOperState.ESTABLISHED
        # check that no event has been created
        event = task.state.events.get(device_name=task.device.name, subindex=PEER_ADDRESS, event_class=BGPEvent)
        assert not event

    @pytest.mark.parametrize(
        "task", ["general-bgp-oper-down", "cisco-bgp-oper-down", "juniper-bgp-oper-down"], indirect=True
    )
    async def test_when_event_is_new_it_should_set_lasttrans(self, task):
        # set initial state
        task.device_state.bgp_peers = {
            PEER_ADDRESS: BGPPeerSession(
                uptime=DEFAULT_UPTIME, admin_status=BGPAdminStatus.START, oper_state=BGPOperState.ESTABLISHED
            )
        }
        await task.run()
        # check that the correct event has been created
        event = task.state.events.get(device_name=task.device.name, subindex=PEER_ADDRESS, event_class=BGPEvent)
        assert event.lasttrans

    @pytest.mark.parametrize(
        "task", ["general-bgp-external-reset", "cisco-bgp-external-reset", "juniper-bgp-external-reset"], indirect=True
    )
    async def test_when_event_transitions_from_not_established_to_established_it_should_update_lasttrans(self, task):
        # create oper down event
        event = task.state.events.get_or_create_event(
            device_name=task.device.name, subindex=PEER_ADDRESS, event_class=BGPEvent
        )
        event.operational_state = BGPOperState.DOWN
        event.admin_status = BGPAdminStatus.STOP
        event.remote_address = PEER_ADDRESS
        event.remote_as = DEFAULT_REMOTE_AS
        event.peer_uptime = 0
        task.state.events.commit(event=event)

        # initial lasttrans should be set by commit()
        initial_lasttrans = event.lasttrans

        await task.run()
        updated_event = task.state.events[event.id]
        assert updated_event.operational_state == BGPOperState.ESTABLISHED
        assert updated_event.lasttrans > initial_lasttrans

    @pytest.mark.parametrize(
        "task", ["general-bgp-admin-down", "cisco-bgp-admin-down", "juniper-bgp-admin-down"], indirect=True
    )
    async def test_when_event_transitions_from_established_to_not_established_it_should_update_lasttrans(self, task):
        initial_lasttrans = now() - timedelta(minutes=5)
        # create oper established event
        event = task.state.events.get_or_create_event(
            device_name=task.device.name, subindex=PEER_ADDRESS, event_class=BGPEvent
        )
        event.operational_state = BGPOperState.ESTABLISHED
        event.admin_status = BGPAdminStatus.RUNNING
        event.remote_address = PEER_ADDRESS
        event.remote_as = DEFAULT_REMOTE_AS
        event.peer_uptime = 0
        event.lasttrans = initial_lasttrans
        task.state.events.commit(event=event)

        await task.run()
        updated_event = task.state.events[event.id]
        assert updated_event.operational_state == BGPOperState.DOWN
        assert updated_event.lasttrans > initial_lasttrans

    @pytest.mark.parametrize(
        "task", ["general-bgp-external-reset", "cisco-bgp-external-reset", "juniper-bgp-external-reset"], indirect=True
    )
    async def test_when_event_transitions_from_not_established_to_established_it_should_update_ac_down(self, task):
        initial_ac_down = timedelta(0)

        # create oper down event
        event = task.state.events.get_or_create_event(
            device_name=task.device.name, subindex=PEER_ADDRESS, event_class=BGPEvent
        )
        event.operational_state = BGPOperState.DOWN
        event.admin_status = BGPAdminStatus.STOP
        event.remote_address = PEER_ADDRESS
        event.remote_as = DEFAULT_REMOTE_AS
        event.peer_uptime = 0
        event.ac_down = initial_ac_down
        task.state.events.commit(event=event)

        await task.run()
        updated_event = task.state.events[event.id]
        assert updated_event.operational_state == BGPOperState.ESTABLISHED
        assert updated_event.ac_down > initial_ac_down


class TestGetBGPStyle:

    @pytest.mark.parametrize("task", ["juniper-bgp"], indirect=True)
    async def test_get_bgp_style_returns_correct_style_for_juniper(self, task):
        assert (await task._get_bgp_style()) == BGPStyle.JUNIPER

    @pytest.mark.parametrize("task", ["cisco-bgp"], indirect=True)
    async def test_get_bgp_style_returns_correct_style_for_cisco(self, task):
        assert (await task._get_bgp_style()) == BGPStyle.CISCO

    @pytest.mark.parametrize("task", ["general-bgp"], indirect=True)
    async def test_get_bgp_style_returns_correct_style_for_general(self, task):
        assert (await task._get_bgp_style()) == BGPStyle.GENERAL

    @pytest.mark.parametrize("task", ["public"], indirect=True)
    async def test_get_bgp_style_returns_correct_style_for_non_bgp_task(self, task):
        assert (await task._get_bgp_style()) is None


class TestGetLocalAs:

    @pytest.mark.parametrize("task", ["juniper-bgp"], indirect=True)
    async def test_get_local_as_returns_correct_value_for_juniper(self, task):
        assert (await task._get_local_as(bgp_style=BGPStyle.JUNIPER)) == 10

    @pytest.mark.parametrize("task", ["cisco-bgp"], indirect=True)
    async def test_get_local_as_returns_correct_value_for_cisco(self, task):
        assert (await task._get_local_as(bgp_style=BGPStyle.CISCO)) == 10

    @pytest.mark.parametrize("task", ["general-bgp"], indirect=True)
    async def test_get_local_as_returns_correct_value_for_general(self, task):
        assert (await task._get_local_as(bgp_style=BGPStyle.GENERAL)) == 10

    @pytest.mark.parametrize("task", ["public"], indirect=True)
    async def test_get_local_as_returns_none_for_non_existent_local_as(self, task):
        assert (await task._get_local_as(bgp_style=BGPStyle.GENERAL)) is None

    @pytest.mark.parametrize("task", ["public"], indirect=True)
    async def test_get_local_as_returns_none_for_non_existent_local_as_with_juniper_bgp_style(self, task):
        assert (await task._get_local_as(bgp_style=BGPStyle.JUNIPER)) is None


class TestBaseBGPRow:
    def test_when_input_is_valid_it_should_not_fail(self):
        assert BaseBGPRow("active", "running", "10.0.42.0", 5, 0)

    def test_when_peer_state_is_invalid_it_should_raise_an_error(self):
        with pytest.raises(ValueError):
            BaseBGPRow("invalid foobar", "running", "10.0.42.0", 5, 0)

    def test_when_peer_admin_status_is_invalid_it_should_raise_an_error(self):
        with pytest.raises(ValueError):
            BaseBGPRow("active", "invalid flimflam", "10.0.42.0", 5, 0)


@pytest.fixture
def task(request, snmpsim, snmp_test_port):
    device = PollDevice(
        name="buick.lab.example.org",
        address="127.0.0.1",
        community=request.param,
        port=snmp_test_port,
    )
    state = ZinoState()
    task = BGPStateMonitorTask(device, state)
    if BGPStyle.CISCO in request.param:
        task.device_state.bgp_style = BGPStyle.CISCO
    elif BGPStyle.JUNIPER in request.param:
        task.device_state.bgp_style = BGPStyle.JUNIPER
    elif BGPStyle.GENERAL in request.param:
        task.device_state.bgp_style = BGPStyle.GENERAL
    yield task
