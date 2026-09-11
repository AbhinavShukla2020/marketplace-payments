from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .models import Base


def create_database(url: str):
    engine = create_async_engine(url, pool_pre_ping=True, isolation_level="SERIALIZABLE")
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def initialize(engine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

