from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")
    
    app_name: str
    env: str
    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int

    google_client_id: str
    
    # Apify Instagram Scraping (direct SDK)
    apify_token: str = ""
    
    # Redis cache
    redis_url: str = "redis://localhost:6379/0"
    
    # YouTube API
    youtube_api_key: str = ""

    # Gemini AI Engine
    gemini_api_key: str = ""

settings = Settings()
