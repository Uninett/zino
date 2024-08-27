import asyncio
import logging
import os
import stat
from functools import wraps
from time import time
from typing import Optional, Union

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


def log_time_spent(logger: Union[logging.Logger, str] = __name__, level: int = logging.DEBUG):
    """Decorator that logs the time taken for a function to execute.  Not suitable for use with async functions"""
    if isinstance(logger, str):
        logger = logging.getLogger(logger)

    def actual_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time()
            try:
                result = func(*args, **kwargs)
            finally:
                end = time()
                logger.log(level, "%s took %s seconds", func.__name__, end - start)
            return result

        return wrapper

    return actual_decorator


def file_is_world_readable(file: str) -> bool:
    """Returns a boolean value indicating if a file is readable by other users than its owner"""
    st_mode = getattr(os.stat(path=file), "st_mode", None)

    return bool(st_mode & stat.S_IROTH)
