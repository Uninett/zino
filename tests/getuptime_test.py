"""Simple tests for the getuptime example program"""

import subprocess

import pytest


def test_get_uptime_should_run_without_error(polldevs_with_localhost, snmpsim):
    confdir = polldevs_with_localhost.parent
    assert subprocess.check_call(["python3", "-m", "zino.getuptime", "localhost"], cwd=confdir) == 0


@pytest.fixture
def polldevs_with_localhost(zino_conf, snmp_test_port):
    polldevs_conf = zino_conf.parent.joinpath("polldevs.cf")
    with open(polldevs_conf, "w") as conf:
        conf.write(
            f"""# polldevs test config
            default interval: 10
            default community: public
            default domain: uninett.no
            default statistics: yes
            default hcounters: yes

            name: localhost
            address: 127.0.0.1
            port: {snmp_test_port}
            """
        )
    yield polldevs_conf
