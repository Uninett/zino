import asyncio
import os
from shutil import which

import pytest
import pytest_asyncio
from retry import retry


@pytest.fixture
def polldevs_conf(tmp_path):
    name = tmp_path.joinpath("polldevs.cf")
    with open(name, "w") as conf:
        conf.write(
            """# polldevs test config
            default interval: 5
            default community: foobar
            default domain: uninett.no
            default statistics: yes
            default hcounters: yes

            name: example-gw
            address: 10.0.42.1

            name: example-gw2
            address: 10.0.43.1"""  # Lack of a new-line here is intentional to test the parser
        )
    yield name


@pytest.fixture
def polldevs_conf_with_single_router(tmp_path):
    name = tmp_path / "polldevs-single.cf"
    with open(name, "w") as conf:
        conf.write(
            """# polldevs test config
            default interval: 5
            default community: foobar
            default domain: uninett.no
            default statistics: yes
            default hcounters: yes

            name: example-gw
            address: 10.0.42.1
            """
        )
    yield name


@pytest.fixture
def polldevs_conf_with_no_routers(tmp_path):
    name = tmp_path / "polldevs-empty.cf"
    with open(name, "w") as conf:
        conf.write(
            """# polldevs test config
            default interval: 5
            default community: foobar
            default domain: uninett.no
            default statistics: yes
            default hcounters: yes
            """
        )
    yield name


@pytest.fixture(scope="session")
def event_loop():
    """Redefine pytest-asyncio's event_loop fixture to have a session scope"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def snmpsim(snmpsimd_path, snmp_fixture_directory, snmp_test_port):
    """Sets up an external snmpsimd process so that SNMP communication can be simulated
    by the test that declares a dependency to this fixture. Data fixtures are loaded
    from the snmp_fixtures subdirectory.
    """
    arguments = [
        f"--data-dir={snmp_fixture_directory}",
        "--log-level=error",
        f"--agent-udpv4-endpoint=127.0.0.1:{snmp_test_port}",
    ]
    print(f"Running {snmpsimd_path} with args: {arguments!r}")
    proc = await asyncio.create_subprocess_exec(snmpsimd_path, *arguments)

    @retry(Exception, tries=3, delay=0.5, backoff=2)
    def _wait_for_snmpsimd():
        if _verify_localhost_snmp_response(snmp_test_port):
            return True
        else:
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
