import asyncio
import threading
from typing import AsyncGenerator, ClassVar, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import async_db_session
from app.pagination import PageDepends


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_db_session() as session:
        yield session


class _AsyncQueueManager:
    _queue: ClassVar[Optional[asyncio.Queue]] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __new__(cls) -> asyncio.Queue:
        if cls._queue is None:
            with cls._lock:
                if cls._queue is None:
                    cls._queue = asyncio.Queue()
        return cls._queue

    @classmethod
    def get_queue(cls) -> asyncio.Queue:
        return cls.__new__(cls)


AsyncQueueManager = _AsyncQueueManager
