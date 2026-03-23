import httpx
from typing import Dict, Any
from app.core.config import settings

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
VIDEO_LIMIT = 15


async def scrape_youtube_channel(username: str) -> Dict[str, Any]:
    """
    Scrape YouTube channel data using YouTube Data API
    
    Args:
        username: YouTube channel username/handle
        
    Returns:
        Dictionary with channel and videos data
        
    Raises:
        Exception: If scraping fails or channel not found
    """
    try:
        async with httpx.AsyncClient() as client:
            # Search for channel by username/handle
            search_url = f"{YOUTUBE_API_BASE}/search"
            search_params = {
                "part": "snippet",
                "q": username,
                "type": "channel",
                "key": settings.youtube_api_key,
                "maxResults": 1
            }
            
            search_response = await client.get(search_url, params=search_params, timeout=30.0)
            search_response.raise_for_status()
            search_data = search_response.json()
            
            if not search_data.get("items"):
                raise Exception(f"YouTube channel '{username}' not found")
            
            channel_id = search_data["items"][0]["id"]["channelId"]
            
            # Get channel details
            channels_url = f"{YOUTUBE_API_BASE}/channels"
            channels_params = {
                "part": "snippet,statistics,contentDetails",
                "id": channel_id,
                "key": settings.youtube_api_key
            }
            
            channels_response = await client.get(channels_url, params=channels_params, timeout=30.0)
            channels_response.raise_for_status()
            channels_data = channels_response.json()
            
            if not channels_data.get("items"):
                raise Exception("Failed to fetch channel details")
            
            channel_info = channels_data["items"][0]
            
            channel_data = {
                "channel_id": channel_id,
                "username": username,
                "title": channel_info["snippet"]["title"],
                "description": channel_info["snippet"]["description"],
                "profile_picture": channel_info["snippet"]["thumbnails"]["default"]["url"],
                "subscribers": int(channel_info["statistics"].get("subscriberCount", 0)),
                "total_views": int(channel_info["statistics"].get("viewCount", 0)),
                "total_videos": int(channel_info["statistics"].get("videoCount", 0)),
                "is_verified": "verified" in channel_info["snippet"].get("description", "").lower(),
            }
            
            # Get uploads playlist ID
            uploads_playlist_id = channel_info["contentDetails"]["relatedPlaylists"]["uploads"]
            
            # Get videos from uploads playlist
            videos_data = []
            playlist_items_url = f"{YOUTUBE_API_BASE}/playlistItems"
            playlist_params = {
                "part": "snippet",
                "playlistId": uploads_playlist_id,
                "key": settings.youtube_api_key,
                "maxResults": VIDEO_LIMIT
            }
            
            playlist_response = await client.get(playlist_items_url, params=playlist_params, timeout=30.0)
            playlist_response.raise_for_status()
            playlist_data = playlist_response.json()
            
            video_ids = [item["snippet"]["resourceId"]["videoId"] for item in playlist_data.get("items", [])]
            
            if video_ids:
                # Get video statistics
                videos_url = f"{YOUTUBE_API_BASE}/videos"
                videos_params = {
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(video_ids),
                    "key": settings.youtube_api_key
                }
                
                videos_response = await client.get(videos_url, params=videos_params, timeout=30.0)
                videos_response.raise_for_status()
                videos_list = videos_response.json()
                
                for video in videos_list.get("items", []):
                    try:
                        duration_str = video["contentDetails"]["duration"]
                        duration_seconds = parse_duration(duration_str)
                        
                        videos_data.append({
                            "video_id": video["id"],
                            "title": video["snippet"]["title"],
                            "description": video["snippet"]["description"],
                            "thumbnail": video["snippet"]["thumbnails"]["default"]["url"],
                            "views": int(video["statistics"].get("viewCount", 0)),
                            "likes": int(video["statistics"].get("likeCount", 0)),
                            "comments": int(video["statistics"].get("commentCount", 0)),
                            "duration": duration_seconds,
                            "published_at": video["snippet"]["publishedAt"],
                        })
                    except (KeyError, ValueError) as e:
                        print(f"⚠️ Error parsing video: {e}")
                        continue
            
            return {
                "channel": channel_data,
                "videos": videos_data,
            }
            
    except httpx.HTTPStatusError as e:
        raise Exception(f"YouTube API error: {str(e)}")
    except httpx.RequestError as e:
        raise Exception(f"Network error while scraping YouTube: {str(e)}")
    except Exception as e:
        raise Exception(f"YouTube scraping error: {str(e)}")


def parse_duration(duration_str: str) -> int:
    """
    Parse ISO 8601 duration string to seconds
    Example: PT1H23M45S -> 5025
    """
    import re
    
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    
    if not match:
        return 0
    
    hours, minutes, seconds = match.groups()
    total_seconds = (
        int(hours or 0) * 3600 +
        int(minutes or 0) * 60 +
        int(seconds or 0)
    )
    
    return total_seconds
