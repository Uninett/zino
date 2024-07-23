from unittest.mock import AsyncMock, MagicMock

import aiodns
import pytest

from zino.utils import reverse_dns


class TestReverseDNS:
    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_should_return_none_for_invalid_ip(self, mock_dnsresolver):
        invalid_ip = "0.0.0.0"

        # Mock DNSResolver.gethostbyaddr to raise DNSError
        mock_gethostbyaddr = AsyncMock(side_effect=aiodns.error.DNSError)
        mock_dnsresolver.gethostbyaddr = mock_gethostbyaddr

        result = await reverse_dns(invalid_ip)
        assert result is None


@pytest.fixture
def mock_dnsresolver(monkeypatch) -> AsyncMock:
    mock_dnsresolver = AsyncMock()
    monkeypatch.setattr("zino.utils.aiodns.DNSResolver", lambda loop: mock_dnsresolver)
    return mock_dnsresolver
