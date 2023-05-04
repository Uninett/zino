import pytest

from zino.config.models import PollDevice
from zino.snmp import SNMP


@pytest.mark.asyncio
async def test_snmp(snmpsim, snmp_test_port):
    device = PollDevice(name="buick.lab.example.org", address="127.0.0.1", port=snmp_test_port)
    snmp = SNMP(device)
    response = await snmp.get("SNMPv2-MIB", "sysUpTime", 0)
    assert response
