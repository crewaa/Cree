from apify_client import ApifyClient
from app.core.config import settings

ACTOR_ID = "apify/instagram-profile-scraper"


def scrape_instagram_creator(username: str) -> dict:
    """
    Call the Apify Instagram Profile Scraper actor directly.
    Returns the raw profile data dict for the given username.
    """
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
