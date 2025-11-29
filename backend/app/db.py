import asyncpg
from typing import Any, Sequence
from .config import settings


class Database:
    def __init__(self) -> None:
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self.pool is None:
            # Keep pool very small to avoid exhausting Supabase session pooler limits
            self.pool = await asyncpg.create_pool(
                dsn=settings.database_url.get_secret_value(), min_size=1, max_size=2
            )

    async def disconnect(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        assert self.pool is not None, "Database not connected"
        return await self.pool.fetchrow(query, *args)

    async def fetch(self, query: str, *args: Any) -> Sequence[asyncpg.Record]:
        assert self.pool is not None, "Database not connected"
        return await self.pool.fetch(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        assert self.pool is not None, "Database not connected"
        return await self.pool.execute(query, *args)

    async def executemany(self, query: str, args: list[tuple[Any, ...]]) -> str:
        assert self.pool is not None, "Database not connected"
        return await self.pool.executemany(query, args)


db = Database()

