from unittest.mock import patch

import pytest

from zino.config.models import PollDevice
from zino.state import ZinoState
from zino.tasks.vendor import VendorTask


class TestVendorTask:
    @patch("zino.state.state", ZinoState())
    @pytest.mark.asyncio
    async def test_run_should_set_enterprise_id(self, snmpsim, snmp_test_port):
        from zino.state import state

        device = PollDevice(name="localhost", address="127.0.0.1", community="public", port=snmp_test_port)
        task = VendorTask(device)
        assert (await task.run()) is None
        assert device.name in state.devices
        # The "public" test fixture is from an HP switch
        assert state.devices[device.name].enterprise_id == 11

    @patch("zino.state.state", ZinoState())
    @pytest.mark.asyncio
    async def test_run_should_do_nothing_when_there_is_no_response(self):
        from zino.state import state

        device = PollDevice(name="localhost", address="127.0.0.1", community="invalid", port=666)
        task = VendorTask(device)
        assert (await task.run()) is None
        assert len(state.devices) == 0
