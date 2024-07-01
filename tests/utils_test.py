from ipaddress import IPv4Address, IPv6Address
from unittest.mock import AsyncMock, MagicMock

import aiodns
import pytest

from zino.utils import parse_ip, reverse_dns


class TestParseIP:
    def test_should_parse_normal_ipv4_string_correctly(self):
        ip_string = "127.0.0.1"
        ip = parse_ip(ip_string)
        assert ip == IPv4Address(ip_string)

    def test_should_parse_normal_ipv6_string_correctly(self):
        ip_string = "13c7:db1c:4430:c826:6333:aed0:e605:3a3b"
        ip = parse_ip(ip_string)
        assert ip == IPv6Address(ip_string)

    def test_should_parse_hexastring_ipv4_correctly(self):
        ip = parse_ip("0x7f000001")
        assert ip == IPv4Address("127.0.0.1")

    def test_should_parse_hexastring_ipv6_correctly(self):
        ip = parse_ip("0x13c7db1c4430c8266333aed0e6053a3b")
        assert ip == IPv6Address("13c7:db1c:4430:c826:6333:aed0:e605:3a3b")

    def test_should_parse_colon_separated_ipv4_octets_correctly(self):
        ip = parse_ip("7f:00:00:01")
        assert ip == IPv4Address("127.0.0.1")

    def test_should_parse_colon_separated_ipv6_octets_correctly(self):
        ip = parse_ip("13:c7:db:1c:44:30:c8:26:63:33:ae:d0:e6:05:3a:3b")
        assert ip == IPv6Address("13c7:db1c:4430:c826:6333:aed0:e605:3a3b")

    def test_should_raise_valueerror_if_invalid_ip_format(self):
        with pytest.raises(ValueError):
            parse_ip("invalidformat")

    def test_should_raise_error_if_invalid_hexastring(self):
        with pytest.raises(ValueError):
            parse_ip("0xinvalidstring")

    def test_should_raise_error_if_invalid_colon_separated_string(self):
        with pytest.raises(ValueError):
            parse_ip(":thisis:just:randomstuff")


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
