from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

connect_args = {}
if is_sqlite:
    connect_args["check_same_thread"] = False

engine_kwargs: dict = {
    "echo": settings.DEBUG,
    "connect_args": connect_args,
}
if not is_sqlite:
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 10

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
