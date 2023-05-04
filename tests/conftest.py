import os
import subprocess
from shutil import which

import pytest
from retry import retry


@pytest.fixture(scope="session")
def snmpsim(snmpsimd_path, snmp_fixture_directory, snmp_test_port):
    """Sets up an external snmpsimd process so that SNMP communication can be simulated
    by the test that declares a dependency to this fixture. Data fixtures are loaded
    from the snmp_fixtures subdirectory.
    """
    command = [
        snmpsimd_path,
        f"--data-dir={snmp_fixture_directory}",
        "--log-level=error",
        f"--agent-udpv4-endpoint=127.0.0.1:{snmp_test_port}",
    ]
    print(f"Running {command!r}")
    proc = subprocess.Popen(command)

    @retry(Exception, tries=3, delay=0.5, backoff=2)
    def _wait_for_snmpsimd():
        if _verify_localhost_snmp_response(snmp_test_port):
            return True
        else:
            proc.poll()
            raise TimeoutError("Still waiting for snmpsimd to listen for queries")

    _wait_for_snmpsimd()

    yield
    proc.kill()


@pytest.fixture(scope="session")
def snmpsimd_path():
    snmpsimd = which("snmpsimd.py")
    assert snmpsimd, "Could not find snmpsimd.py"
    yield snmpsimd


@pytest.fixture(scope="session")
def snmp_fixture_directory():
    this_directory = os.path.dirname(__file__)
    fixture_dir = os.path.join(this_directory, "snmp_fixtures")
    assert os.path.isdir(fixture_dir)
    yield fixture_dir


@pytest.fixture(scope="session")
def snmp_test_port():
    yield 1024


def _verify_localhost_snmp_response(port: int):
    """Verifies that the snmpsimd fixture process is responding, by using PySNMP directly to query it."""

    from pysnmp.hlapi import (
        CommunityData,
        ContextData,
        ObjectIdentity,
        ObjectType,
        SnmpEngine,
        UdpTransportTarget,
        nextCmd,
    )

    responses = nextCmd(
        SnmpEngine(),
        CommunityData("public"),
        UdpTransportTarget(("localhost", port)),
        ContextData(),
        ObjectType(ObjectIdentity("SNMPv2-MIB", "sysObjectID")),
    )
    return next(responses)
