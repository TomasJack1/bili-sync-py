from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

async_db_engine = create_async_engine("sqlite+aiosqlite:///video.db")
async_db_session = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_db_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def create_table() -> None:
    async with async_db_engine.connect() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
