import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.modules.users.models import SavedCreator

async def test():
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        res = await db.execute("SELECT * FROM saved_creators;")
        for row in res.fetchall():
            print(dict(row._mapping))

asyncio.run(test())
