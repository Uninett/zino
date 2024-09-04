import logging
import os
import stat
from unittest.mock import AsyncMock, MagicMock

import aiodns
import pytest

from zino.utils import file_is_world_readable, log_time_spent, reverse_dns


class TestReverseDNS:

    async def test_should_return_reverse_dns_for_valid_ip(self, mock_dnsresolver):
        valid_ip = "8.8.8.8"
        reverse_dns_value = "reverse.dns.example.com"

        # Create mock for return value of gethostbyaddr
        mock_gethostbyaddr_return_value = MagicMock()
        mock_gethostbyaddr_return_value.configure_mock(name=reverse_dns_value, aliases=[], addresses=[valid_ip])

        # Create gethostbyaddr async mock
        mock_gethostbyaddr = AsyncMock(return_value=mock_gethostbyaddr_return_value)

        # Mock DNSRsolver.gethostbyaddr function
        mock_dnsresolver.gethostbyaddr = mock_gethostbyaddr

        result = await reverse_dns(valid_ip)
        assert result == reverse_dns_value

    async def test_should_return_none_for_invalid_ip(self, mock_dnsresolver):
        invalid_ip = "0.0.0.0"

        # Mock DNSResolver.gethostbyaddr to raise DNSError
        mock_gethostbyaddr = AsyncMock(side_effect=aiodns.error.DNSError)
        mock_dnsresolver.gethostbyaddr = mock_gethostbyaddr

        result = await reverse_dns(invalid_ip)
        assert result is None


class TestLogTimeSpent:
    def test_when_logger_is_specified_it_should_log_time_spent_using_that_logger(self, caplog):
        @log_time_spent(logger="test_logger", level=logging.DEBUG)
        def test_function():
            pass

        with caplog.at_level(logging.DEBUG):
            test_function()

        assert any(
            record.name == "test_logger"
            and "took" in record.msg
            and "ms" in record.msg
            and "test_function" in record.args
            for record in caplog.records
        )

    async def test_when_decorated_function_is_async_it_should_log_time_spent(self, caplog):
        @log_time_spent(level=logging.DEBUG)
        async def test_function():
            pass

        with caplog.at_level(logging.DEBUG):
            await test_function()

        assert any(
            "took" in record.msg and "ms" in record.msg and "test_function" in record.args for record in caplog.records
        )


@pytest.fixture
def mock_dnsresolver(monkeypatch) -> AsyncMock:
    mock_dnsresolver = AsyncMock()
    monkeypatch.setattr("zino.utils.aiodns.DNSResolver", lambda loop: mock_dnsresolver)
    return mock_dnsresolver


class TestFileIsReadableByOthers:
    def test_return_true_if_file_is_world_readable(self, secrets_file):
        assert file_is_world_readable(secrets_file)

    def test_return_if_file_is_only_readable_by_owner(self, tmp_path):
        name = tmp_path / "owner-secrets"
        with open(name, "w") as conf:
            conf.write("""user1 password123""")
        os.chmod(name, mode=stat.S_IRWXU)

        assert not file_is_world_readable(name)
