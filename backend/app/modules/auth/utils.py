import httpx
from fastapi import HTTPException
from app.core.config import settings

GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"

async def verify_google_token(id_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            GOOGLE_TOKEN_INFO_URL,
            params={"id_token": id_token},
        )

    if resp.status_code != 200:
        raise HTTPException(401, "Invalid Google token")

    data = resp.json()

    if data["aud"] != settings.google_client_id:
        raise HTTPException(401, "Invalid Google audience")

    return data
