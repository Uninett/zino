import asyncio
import inspect
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


def log_time_spent(
    logger: Union[logging.Logger, str] = __name__,
    level: int = logging.DEBUG,
    limit: Union[int, float] = 0.0,
    formatter: Optional[callable] = None,
) -> callable:
    """Decorator that logs the time taken for a function to execute"""
    if isinstance(logger, str):
        logger = logging.getLogger(logger)

    def actual_decorator(func: callable) -> callable:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def wrapper(*args, **kwargs):
                if formatter:
                    func_repr = f"{func.__name__}({formatter(args, kwargs)})"
                else:
                    func_repr = func.__name__
                start = time()
                try:
                    result = await func(*args, **kwargs)
                finally:
                    end = time()
                    duration = end - start
                    if duration >= limit:
                        logger.log(
                            level,
                            "%s took %.3f ms",
                            func_repr,
                            duration * 1000.0,
                        )
                return result

        else:

            @wraps(func)
            def wrapper(*args, **kwargs):
                if formatter:
                    func_repr = f"{func.__name__}({formatter(args, kwargs)})"
                else:
                    func_repr = func.__name__
                start = time()
                try:
                    result = func(*args, **kwargs)
                finally:
                    end = time()
                    duration = end - start
                    if duration >= limit:
                        logger.log(
                            level,
                            "%s took %.3f ms",
                            func_repr,
                            duration * 1000.0,
                        )
                return result

        return wrapper

    return actual_decorator


def file_is_world_readable(file: str) -> bool:
    """Returns a boolean value indicating if a file is readable by other users than its owner"""
    st_mode = getattr(os.stat(path=file), "st_mode", None)

    return bool(st_mode & stat.S_IROTH)
