import asyncio
import ipaddress
import os
from datetime import timedelta
from shutil import which

import pytest
import pytest_asyncio
from retry import retry

from zino.planned_maintenance import PlannedMaintenances
from zino.state import ZinoState
from zino.statemodels import (
    DeviceMaintenance,
    DeviceState,
    InterfaceState,
    MatchType,
    Port,
    PortStateMaintenance,
)
from zino.time import now
from zino.trapd import netsnmpy_backend, pysnmp_backend


def pytest_configure(config):
    import os

    # Load the default SNMP back-end for the test suite.  Tests for specific back-end will import directly from those.
    from zino.snmp import import_snmp_backend
    from zino.trapd import import_trap_backend

    import_snmp_backend()
    import_trap_backend()

    from netsnmpy import netsnmp

    from zino.snmp import get_vendored_mib_directory

    # Ensure that the vendored MIBs are loaded
    os.environ["MIBS"] = "ALL"
    vendored_mibs = get_vendored_mib_directory()
    print(f"Setting MIBDIRS to {vendored_mibs}")
    os.environ["MIBDIRS"] = f"{vendored_mibs}"
    netsnmp.load_mibs()
    modules = ", ".join(sorted(netsnmp.get_loaded_mibs()))
    print(f"Loaded MIB modules: {modules}")

    # Every test should operate with a fresh SNMP session object:
    # Disable re-use of SNMP sessions for testing purposes
    from zino import snmp

    snmp._snmp_sessions = None


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


@pytest.fixture
def invalid_polldevs_conf(tmp_path):
    name = tmp_path.joinpath("polldevs.cf")
    with open(name, "w") as conf:
        conf.write(
            """# polldevs test config
            lalala
            """
        )
    yield name


@pytest.fixture
def secrets_file(tmp_path):
    name = tmp_path / "secrets"
    with open(name, "w") as conf:
        conf.write("""user1 password123""")
    yield name


@pytest.fixture
def zino_conf(tmp_path, polldevs_conf_with_no_routers, secrets_file):
    name = tmp_path / "zino.toml"
    with open(name, "w") as conf:
        conf.write(
            f"""
            [authentication]
            file = "{secrets_file}"
            [polling]
            file = "{polldevs_conf_with_no_routers}"
            """
        )
    yield name


@pytest.fixture
def zino_conf_with_non_existent_pollfile(tmp_path, secrets_file):
    name = tmp_path / "zino-no-pollfile.toml"
    with open(name, "w") as conf:
        conf.write(
            f"""
            [authentication]
            file = "{secrets_file}"
            [polling]
            file = "{tmp_path}/non-existent-pollfile.cf"
            """
        )
    yield name


@pytest.fixture
def invalid_zino_conf(tmp_path):
    name = tmp_path / "invalid-zino.toml"
    with open(name, "w") as conf:
        conf.write(
            """
                [archiving]
                old_events_dir = abc
            """
        )
    yield name


@pytest.fixture
def invalid_values_zino_conf(tmp_path):
    name = tmp_path / "invalid-config-values.toml"
    with open(name, "w") as conf:
        conf.write(
            """
                [archiving]
                old_events_dir = false
            """
        )
    yield name


@pytest.fixture
def extra_keys_zino_conf(tmp_path):
    name = tmp_path / "extra-keys.toml"
    with open(name, "w") as conf:
        conf.write(
            """
                [archiving]
                typo = "old-zino-events"
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
    async def _wait_for_snmpsimd():
        if await _verify_localhost_snmp_response(snmp_test_port):
            return True
        else:
            raise TimeoutError("Still waiting for snmpsimd to listen for queries")

    await _wait_for_snmpsimd()

    yield
    proc.kill()


@pytest.fixture(scope="session")
def snmpsimd_path():
    snmpsimd = which("snmpsim-command-responder")
    assert snmpsimd, "Could not find snmpsim-command-responder"
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


@pytest.fixture
def state_with_localhost():
    localhost = ipaddress.ip_address("127.0.0.1")
    state = ZinoState()
    state.devices.devices["localhost"] = DeviceState(name="localhost", addresses={localhost})
    state.addresses[localhost] = "localhost"
    yield state


@pytest_asyncio.fixture
async def localhost_pysnmp_receiver(state_with_localhost, unused_udp_port, event_loop) -> pysnmp_backend.TrapReceiver:
    """Yields a TrapReceiver instance with a standardized setup for running external tests on localhost"""
    receiver = pysnmp_backend.TrapReceiver(
        address="127.0.0.1", port=unused_udp_port, loop=event_loop, state=state_with_localhost
    )
    receiver.add_community("public")
    await receiver.open()
    yield receiver
    receiver.close()


@pytest_asyncio.fixture
async def localhost_netsnmpy_receiver(
    state_with_localhost, unused_udp_port, event_loop
) -> netsnmpy_backend.TrapReceiver:
    """Yields a TrapReceiver instance with a standardized setup for running external tests on localhost"""
    receiver = netsnmpy_backend.TrapReceiver(
        address="127.0.0.1", port=unused_udp_port, loop=event_loop, state=state_with_localhost
    )
    receiver.add_community("public")
    await receiver.open()
    yield receiver
    receiver.close()


async def _verify_localhost_snmp_response(port: int):
    """Verifies that the snmpsimd fixture process is responding, by using PySNMP directly to query it."""

    from pysnmp.hlapi.asyncio import (
        CommunityData,
        ContextData,
        ObjectIdentity,
        ObjectType,
        SnmpEngine,
        UdpTransportTarget,
        nextCmd,
    )

    responses = await nextCmd(
        SnmpEngine(),
        CommunityData("public"),
        UdpTransportTarget(("localhost", port)),
        ContextData(),
        ObjectType(ObjectIdentity("SNMPv2-MIB", "sysObjectID")),
    )
    return responses


@pytest.fixture
def state_with_localhost_with_port(state_with_localhost):
    port = Port(ifindex=1, ifdescr="eth0", ifalias="eth0alias", state=InterfaceState.UP)
    device = state_with_localhost.devices.devices["localhost"]
    device.boot_time = now() - timedelta(minutes=10)
    device.ports[port.ifindex] = port
    yield state_with_localhost


@pytest.fixture
def pms():
    return PlannedMaintenances()


@pytest.fixture
def active_device_pm(pms):
    return pms.create_planned_maintenance(
        start_time=now() - timedelta(days=1),
        end_time=now() + timedelta(days=1),
        pm_class=DeviceMaintenance,
        match_type=MatchType.EXACT,
        match_expression="device",
        match_device="device",
    )


@pytest.fixture
def active_portstate_pm(pms):
    return pms.create_planned_maintenance(
        start_time=now() - timedelta(days=1),
        end_time=now() + timedelta(days=1),
        pm_class=PortStateMaintenance,
        match_type=MatchType.REGEXP,
        match_expression="port",
        match_device="device",
    )


@pytest.fixture
def ended_pm(pms):
    return pms.create_planned_maintenance(
        start_time=now() - timedelta(days=1),
        end_time=now() - timedelta(minutes=10),
        pm_class=DeviceMaintenance,
        match_type=MatchType.EXACT,
        match_expression="device",
        match_device="device",
    )
