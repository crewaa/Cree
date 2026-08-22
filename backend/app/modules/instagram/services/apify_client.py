from apify_client import ApifyClient
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

ACTOR_ID = "apify/instagram-profile-scraper"


def _scrape_instagram_creator_sync(username: str) -> dict:
    """
    Call the Apify Instagram Profile Scraper actor. Blocking.

    `.call()` waits for the actor run to finish, which takes tens of seconds.
    Do not call this directly from async code — use the async wrapper below.
    """
    if not settings.apify_token:
        raise ValueError(
            "APIFY_TOKEN is not configured; Instagram scraping is unavailable"
        )

    client = ApifyClient(settings.apify_token)

    run_input = {
        "usernames": [username],
        "resultsLimit": 12,
        "proxy": {"useApifyProxy": True},
    }

    run = client.actor(ACTOR_ID).call(run_input=run_input)

    dataset_id = run["defaultDatasetId"]
    items = list(client.dataset(dataset_id).iterate_items())

    if not items:
        raise ValueError(f"Creator '{username}' not found on Instagram")

    return items[0]


async def scrape_instagram_creator(username: str) -> dict:
    """
    Async wrapper around the blocking Apify SDK call.

    The scrape runs inside a background task on the event loop; without the
    threadpool hop it stalls every other request on that worker for the whole
    actor run.
    """
    return await run_in_threadpool(_scrape_instagram_creator_sync, username)
