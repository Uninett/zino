import asyncio
from typing import Optional

import aiodns


async def reverse_dns(ip: str) -> Optional[str]:
    """Returns hostname for given IP address or None if reverse DNS lookup fails"""
    loop = asyncio.get_event_loop()
    resolver = aiodns.DNSResolver(loop=loop)
    try:
        response = await resolver.gethostbyaddr(ip)
        return response.name
    except aiodns.error.DNSError:
        return None
