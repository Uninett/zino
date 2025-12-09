"""Tests for max_repetitions parameter handling in SNMP backends.

These tests verify that the max_repetitions parameter is correctly passed through
the SNMP backend methods, using the device configuration, explicit parameter,
or default values as appropriate.
"""

from unittest.mock import AsyncMock, patch

import pytest

from zino.config.models import PollDevice

# Check if netsnmpy is available
try:
    import netsnmpy

    HAVE_NETSNMP = True
except ImportError:
    HAVE_NETSNMP = False


@pytest.mark.skipif(not HAVE_NETSNMP, reason="netsnmp-cffi not available")
class TestNetsnmpyBackendMaxRepetitions:
    """Tests for max_repetitions in the netsnmpy backend"""

    @pytest.fixture
    def device_with_max_repetitions(self):
        return PollDevice(name="test-device", address="127.0.0.1", max_repetitions=15)

    @pytest.fixture
    def device_without_max_repetitions(self):
        return PollDevice(name="test-device", address="127.0.0.1")

    # getbulk tests (default: 1)

    @pytest.mark.asyncio
    async def test_when_device_has_max_repetitions_getbulk_should_use_it(self, device_with_max_repetitions):
        from zino.snmp.netsnmpy_backend import SNMP as NetSnmp

        snmp = NetSnmp(device_with_max_repetitions)
        with patch.object(snmp.session, "agetbulk", new_callable=AsyncMock) as mock_agetbulk:
            mock_agetbulk.return_value = []
            await snmp.getbulk("1.3.6.1.2.1.1.1.0")
            mock_agetbulk.assert_called_once_with(
                "1.3.6.1.2.1.1.1.0",
                max_repetitions=15,
            )

    @pytest.mark.asyncio
    async def test_when_parameter_is_given_getbulk_should_override_device_config(self, device_with_max_repetitions):
        from zino.snmp.netsnmpy_backend import SNMP as NetSnmp

        snmp = NetSnmp(device_with_max_repetitions)
        with patch.object(snmp.session, "agetbulk", new_callable=AsyncMock) as mock_agetbulk:
            mock_agetbulk.return_value = []
            await snmp.getbulk("1.3.6.1.2.1.1.1.0", max_repetitions=20)
            mock_agetbulk.assert_called_once_with(
                "1.3.6.1.2.1.1.1.0",
                max_repetitions=20,
            )

    @pytest.mark.asyncio
    async def test_when_device_has_no_max_repetitions_getbulk_should_use_default(self, device_without_max_repetitions):
        from zino.snmp.netsnmpy_backend import SNMP as NetSnmp

        snmp = NetSnmp(device_without_max_repetitions)
        with patch.object(snmp.session, "agetbulk", new_callable=AsyncMock) as mock_agetbulk:
            mock_agetbulk.return_value = []
            await snmp.getbulk("1.3.6.1.2.1.1.1.0")
            mock_agetbulk.assert_called_once_with(
                "1.3.6.1.2.1.1.1.0",
                max_repetitions=1,
            )

    # getbulk2 tests (default: 5)

    @pytest.mark.asyncio
    async def test_when_device_has_max_repetitions_getbulk2_should_use_it(self, device_with_max_repetitions):
        from zino.snmp.netsnmpy_backend import SNMP as NetSnmp

        snmp = NetSnmp(device_with_max_repetitions)
        with patch.object(snmp.session, "agetbulk", new_callable=AsyncMock) as mock_agetbulk:
            mock_agetbulk.return_value = []
            await snmp.getbulk2(("IF-MIB", "ifName"), ("IF-MIB", "ifAlias"))
            mock_agetbulk.assert_called_once()
            _, kwargs = mock_agetbulk.call_args
            assert kwargs["max_repetitions"] == 15

    @pytest.mark.asyncio
    async def test_when_parameter_is_given_getbulk2_should_override_device_config(self, device_with_max_repetitions):
        from zino.snmp.netsnmpy_backend import SNMP as NetSnmp

        snmp = NetSnmp(device_with_max_repetitions)
        with patch.object(snmp.session, "agetbulk", new_callable=AsyncMock) as mock_agetbulk:
            mock_agetbulk.return_value = []
            await snmp.getbulk2(("IF-MIB", "ifName"), ("IF-MIB", "ifAlias"), max_repetitions=25)
            mock_agetbulk.assert_called_once()
            _, kwargs = mock_agetbulk.call_args
            assert kwargs["max_repetitions"] == 25

    @pytest.mark.asyncio
    async def test_when_device_has_no_max_repetitions_getbulk2_should_use_default(self, device_without_max_repetitions):
        from zino.snmp.netsnmpy_backend import SNMP as NetSnmp

        snmp = NetSnmp(device_without_max_repetitions)
        with patch.object(snmp.session, "agetbulk", new_callable=AsyncMock) as mock_agetbulk:
            mock_agetbulk.return_value = []
            await snmp.getbulk2(("IF-MIB", "ifName"), ("IF-MIB", "ifAlias"))
            mock_agetbulk.assert_called_once()
            _, kwargs = mock_agetbulk.call_args
            assert kwargs["max_repetitions"] == 5

    # bulkwalk tests (default: 5)

    @pytest.mark.asyncio
    async def test_when_device_has_max_repetitions_bulkwalk_should_use_it(self, device_with_max_repetitions):
        from zino.snmp.netsnmpy_backend import SNMP as NetSnmp

        snmp = NetSnmp(device_with_max_repetitions)
        with patch.object(snmp.session, "agetbulk", new_callable=AsyncMock) as mock_agetbulk:
            mock_agetbulk.return_value = []
            await snmp.bulkwalk("1.3.6.1.2.1.1.1.0")
            mock_agetbulk.assert_called_once()
            _, kwargs = mock_agetbulk.call_args
            assert kwargs["max_repetitions"] == 15

    @pytest.mark.asyncio
    async def test_when_parameter_is_given_bulkwalk_should_override_device_config(self, device_with_max_repetitions):
        from zino.snmp.netsnmpy_backend import SNMP as NetSnmp

        snmp = NetSnmp(device_with_max_repetitions)
        with patch.object(snmp.session, "agetbulk", new_callable=AsyncMock) as mock_agetbulk:
            mock_agetbulk.return_value = []
            await snmp.bulkwalk("1.3.6.1.2.1.1.1.0", max_repetitions=30)
            mock_agetbulk.assert_called_once()
            _, kwargs = mock_agetbulk.call_args
            assert kwargs["max_repetitions"] == 30

    @pytest.mark.asyncio
    async def test_when_device_has_no_max_repetitions_bulkwalk_should_use_default(self, device_without_max_repetitions):
        from zino.snmp.netsnmpy_backend import SNMP as NetSnmp

        snmp = NetSnmp(device_without_max_repetitions)
        with patch.object(snmp.session, "agetbulk", new_callable=AsyncMock) as mock_agetbulk:
            mock_agetbulk.return_value = []
            await snmp.bulkwalk("1.3.6.1.2.1.1.1.0")
            mock_agetbulk.assert_called_once()
            _, kwargs = mock_agetbulk.call_args
            assert kwargs["max_repetitions"] == 5

    # sparsewalk tests (default: 5)

    @pytest.mark.asyncio
    async def test_when_device_has_max_repetitions_sparsewalk_should_use_it(self, device_with_max_repetitions):
        from zino.snmp.netsnmpy_backend import SNMP as NetSnmp

        snmp = NetSnmp(device_with_max_repetitions)
        with patch.object(snmp.session, "agetbulk", new_callable=AsyncMock) as mock_agetbulk:
            mock_agetbulk.return_value = []
            await snmp.sparsewalk(("IF-MIB", "ifName"), ("IF-MIB", "ifAlias"))
            mock_agetbulk.assert_called_once()
            _, kwargs = mock_agetbulk.call_args
            assert kwargs["max_repetitions"] == 15

    @pytest.mark.asyncio
    async def test_when_parameter_is_given_sparsewalk_should_override_device_config(self, device_with_max_repetitions):
        from zino.snmp.netsnmpy_backend import SNMP as NetSnmp

        snmp = NetSnmp(device_with_max_repetitions)
        with patch.object(snmp.session, "agetbulk", new_callable=AsyncMock) as mock_agetbulk:
            mock_agetbulk.return_value = []
            await snmp.sparsewalk(("IF-MIB", "ifName"), ("IF-MIB", "ifAlias"), max_repetitions=35)
            mock_agetbulk.assert_called_once()
            _, kwargs = mock_agetbulk.call_args
            assert kwargs["max_repetitions"] == 35

    @pytest.mark.asyncio
    async def test_when_device_has_no_max_repetitions_sparsewalk_should_use_default(self, device_without_max_repetitions):
        from zino.snmp.netsnmpy_backend import SNMP as NetSnmp

        snmp = NetSnmp(device_without_max_repetitions)
        with patch.object(snmp.session, "agetbulk", new_callable=AsyncMock) as mock_agetbulk:
            mock_agetbulk.return_value = []
            await snmp.sparsewalk(("IF-MIB", "ifName"), ("IF-MIB", "ifAlias"))
            mock_agetbulk.assert_called_once()
            _, kwargs = mock_agetbulk.call_args
            assert kwargs["max_repetitions"] == 5


class TestPysnmpBackendMaxRepetitions:
    """Tests for max_repetitions in the pysnmp backend"""

    @pytest.fixture
    def device_with_max_repetitions(self):
        return PollDevice(name="test-device", address="127.0.0.1", max_repetitions=15)

    @pytest.fixture
    def device_without_max_repetitions(self):
        return PollDevice(name="test-device", address="127.0.0.1")

    # getbulk tests (default: 1)

    @pytest.mark.asyncio
    async def test_when_device_has_max_repetitions_getbulk_should_use_it(self, device_with_max_repetitions):
        from zino.snmp.pysnmp_backend import SNMP as PySnmp

        snmp = PySnmp(device_with_max_repetitions)
        with patch.object(snmp, "_getbulk", new_callable=AsyncMock) as mock_getbulk:
            mock_getbulk.return_value = []
            await snmp.getbulk("1.3.6.1.2.1.1.1.0")
            mock_getbulk.assert_called_once()
            args, _ = mock_getbulk.call_args
            assert args[1] == 15  # max_repetitions is second positional arg

    @pytest.mark.asyncio
    async def test_when_parameter_is_given_getbulk_should_override_device_config(self, device_with_max_repetitions):
        from zino.snmp.pysnmp_backend import SNMP as PySnmp

        snmp = PySnmp(device_with_max_repetitions)
        with patch.object(snmp, "_getbulk", new_callable=AsyncMock) as mock_getbulk:
            mock_getbulk.return_value = []
            await snmp.getbulk("1.3.6.1.2.1.1.1.0", max_repetitions=20)
            mock_getbulk.assert_called_once()
            args, _ = mock_getbulk.call_args
            assert args[1] == 20

    @pytest.mark.asyncio
    async def test_when_device_has_no_max_repetitions_getbulk_should_use_default(self, device_without_max_repetitions):
        from zino.snmp.pysnmp_backend import SNMP as PySnmp

        snmp = PySnmp(device_without_max_repetitions)
        with patch.object(snmp, "_getbulk", new_callable=AsyncMock) as mock_getbulk:
            mock_getbulk.return_value = []
            await snmp.getbulk("1.3.6.1.2.1.1.1.0")
            mock_getbulk.assert_called_once()
            args, _ = mock_getbulk.call_args
            assert args[1] == 1

    # getbulk2 tests (default: 10)

    @pytest.mark.asyncio
    async def test_when_device_has_max_repetitions_getbulk2_should_use_it(self, device_with_max_repetitions):
        from zino.snmp.pysnmp_backend import SNMP as PySnmp

        snmp = PySnmp(device_with_max_repetitions)
        with patch.object(snmp, "_getbulk2", new_callable=AsyncMock) as mock_getbulk2:
            mock_getbulk2.return_value = []
            await snmp.getbulk2(("IF-MIB", "ifName"), ("IF-MIB", "ifAlias"))
            mock_getbulk2.assert_called_once()
            _, kwargs = mock_getbulk2.call_args
            assert kwargs["max_repetitions"] == 15

    @pytest.mark.asyncio
    async def test_when_parameter_is_given_getbulk2_should_override_device_config(self, device_with_max_repetitions):
        from zino.snmp.pysnmp_backend import SNMP as PySnmp

        snmp = PySnmp(device_with_max_repetitions)
        with patch.object(snmp, "_getbulk2", new_callable=AsyncMock) as mock_getbulk2:
            mock_getbulk2.return_value = []
            await snmp.getbulk2(("IF-MIB", "ifName"), ("IF-MIB", "ifAlias"), max_repetitions=25)
            mock_getbulk2.assert_called_once()
            _, kwargs = mock_getbulk2.call_args
            assert kwargs["max_repetitions"] == 25

    @pytest.mark.asyncio
    async def test_when_device_has_no_max_repetitions_getbulk2_should_use_default(self, device_without_max_repetitions):
        from zino.snmp.pysnmp_backend import SNMP as PySnmp

        snmp = PySnmp(device_without_max_repetitions)
        with patch.object(snmp, "_getbulk2", new_callable=AsyncMock) as mock_getbulk2:
            mock_getbulk2.return_value = []
            await snmp.getbulk2(("IF-MIB", "ifName"), ("IF-MIB", "ifAlias"))
            mock_getbulk2.assert_called_once()
            _, kwargs = mock_getbulk2.call_args
            assert kwargs["max_repetitions"] == 10

    # bulkwalk tests (default: 10)

    @pytest.mark.asyncio
    async def test_when_device_has_max_repetitions_bulkwalk_should_use_it(self, device_with_max_repetitions):
        from zino.snmp.pysnmp_backend import SNMP as PySnmp

        snmp = PySnmp(device_with_max_repetitions)
        with patch.object(snmp, "_getbulk", new_callable=AsyncMock) as mock_getbulk:
            mock_getbulk.return_value = []
            await snmp.bulkwalk("IF-MIB", "ifName")
            mock_getbulk.assert_called_once()
            args, _ = mock_getbulk.call_args
            assert args[1] == 15

    @pytest.mark.asyncio
    async def test_when_parameter_is_given_bulkwalk_should_override_device_config(self, device_with_max_repetitions):
        from zino.snmp.pysnmp_backend import SNMP as PySnmp

        snmp = PySnmp(device_with_max_repetitions)
        with patch.object(snmp, "_getbulk", new_callable=AsyncMock) as mock_getbulk:
            mock_getbulk.return_value = []
            await snmp.bulkwalk("IF-MIB", "ifName", max_repetitions=30)
            mock_getbulk.assert_called_once()
            args, _ = mock_getbulk.call_args
            assert args[1] == 30

    @pytest.mark.asyncio
    async def test_when_device_has_no_max_repetitions_bulkwalk_should_use_default(self, device_without_max_repetitions):
        from zino.snmp.pysnmp_backend import SNMP as PySnmp

        snmp = PySnmp(device_without_max_repetitions)
        with patch.object(snmp, "_getbulk", new_callable=AsyncMock) as mock_getbulk:
            mock_getbulk.return_value = []
            await snmp.bulkwalk("IF-MIB", "ifName")
            mock_getbulk.assert_called_once()
            args, _ = mock_getbulk.call_args
            assert args[1] == 10

    # sparsewalk tests (default: 10)

    @pytest.mark.asyncio
    async def test_when_device_has_max_repetitions_sparsewalk_should_use_it(self, device_with_max_repetitions):
        from zino.snmp.pysnmp_backend import SNMP as PySnmp

        snmp = PySnmp(device_with_max_repetitions)
        with patch.object(snmp, "_getbulk2", new_callable=AsyncMock) as mock_getbulk2:
            mock_getbulk2.return_value = []
            await snmp.sparsewalk(("IF-MIB", "ifName"), ("IF-MIB", "ifAlias"))
            mock_getbulk2.assert_called_once()
            _, kwargs = mock_getbulk2.call_args
            assert kwargs["max_repetitions"] == 15

    @pytest.mark.asyncio
    async def test_when_parameter_is_given_sparsewalk_should_override_device_config(self, device_with_max_repetitions):
        from zino.snmp.pysnmp_backend import SNMP as PySnmp

        snmp = PySnmp(device_with_max_repetitions)
        with patch.object(snmp, "_getbulk2", new_callable=AsyncMock) as mock_getbulk2:
            mock_getbulk2.return_value = []
            await snmp.sparsewalk(("IF-MIB", "ifName"), ("IF-MIB", "ifAlias"), max_repetitions=35)
            mock_getbulk2.assert_called_once()
            _, kwargs = mock_getbulk2.call_args
            assert kwargs["max_repetitions"] == 35

    @pytest.mark.asyncio
    async def test_when_device_has_no_max_repetitions_sparsewalk_should_use_default(self, device_without_max_repetitions):
        from zino.snmp.pysnmp_backend import SNMP as PySnmp

        snmp = PySnmp(device_without_max_repetitions)
        with patch.object(snmp, "_getbulk2", new_callable=AsyncMock) as mock_getbulk2:
            mock_getbulk2.return_value = []
            await snmp.sparsewalk(("IF-MIB", "ifName"), ("IF-MIB", "ifAlias"))
            mock_getbulk2.assert_called_once()
            _, kwargs = mock_getbulk2.call_args
            assert kwargs["max_repetitions"] == 10
