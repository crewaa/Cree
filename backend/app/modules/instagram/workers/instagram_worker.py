import asyncio
from celery import Celery
from app.core.database import AsyncSessionLocal
from app.modules.instagram.services.instagram_scrapper import scrape_and_store


celery = Celery("worker", broker="redis://localhost:6379/0")

@celery.task
def run_scrape(user_id):
    """Celery task to run Instagram scraping"""
    async def async_scrape():
        await scrape_and_store(user_id)
    
    asyncio.run(async_scrape())
