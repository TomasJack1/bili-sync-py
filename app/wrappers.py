from functools import wraps
from typing import Any, Callable, Coroutine, ParamSpec, TypeVar

import aiolimiter
from aiolimiter import AsyncLimiter

from app.logger import logger

P = ParamSpec("P")
R = TypeVar("R")
AsyncFunc = Callable[P, Coroutine[Any, Any, R]]


def rate_limit() -> Callable:
    default_max_ratio: float = 1.0
    default_period: float = 2.0

    _limiter_instance: AsyncLimiter = aiolimiter.AsyncLimiter(
        default_max_ratio,
        default_period,
    )

    def decorator(_func: AsyncFunc) -> AsyncFunc:
        @wraps(_func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            async with _limiter_instance:
                return await _func(*args, **kwargs)

        return wrapper

    return decorator


def background_worker(func: AsyncFunc) -> AsyncFunc:
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            logger.exception(exc)
            return await wrapper(*args, **kwargs)

    return wrapper
