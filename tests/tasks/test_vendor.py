import pytest

from zino.config.models import PollDevice
from zino.state import ZinoState
from zino.tasks.vendor import VendorTask


class TestVendorTask:
    @pytest.mark.asyncio
    async def test_run_should_set_enterprise_id(self, snmpsim, snmp_test_port):
        device = PollDevice(name="localhost", address="127.0.0.1", community="public", port=snmp_test_port)
        state = ZinoState()
        task = VendorTask(device, state)
        assert (await task.run()) is None
        assert device.name in state.devices
        # The "public" test fixture is from an HP switch
        assert state.devices[device.name].enterprise_id == 11

    @pytest.mark.asyncio
    async def test_run_should_do_nothing_when_there_is_no_response(self):
        device = PollDevice(name="localhost", address="127.0.0.1", community="invalid", port=666)
        state = ZinoState()
        task = VendorTask(device, state)
        assert (await task.run()) is None
        assert len(state.devices) == 0
