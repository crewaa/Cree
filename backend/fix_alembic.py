import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def main():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.execute(
            __import__('sqlalchemy').text("UPDATE alembic_version SET version_num='c4a1b2d9e6f0'")
        )
    print("Alembic version reset")

asyncio.run(main())
