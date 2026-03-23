import os
import re
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
MAX_VIDEOS = 15

if not YOUTUBE_API_KEY:
    raise ValueError("YOUTUBE_API_KEY not found")

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

CHANNEL_ID_REGEX = r"^UC[a-zA-Z0-9_-]{22}$"

# -------------------------
# RESOLVER
# -------------------------

def resolve_channel_id(input_value: str) -> str:
    input_value = input_value.strip()

    if re.match(CHANNEL_ID_REGEX, input_value):
        return input_value

    if "youtube.com" in input_value:
        return _resolve_from_url(input_value)

    return _resolve_from_handle(input_value)

def _resolve_from_url(url: str) -> str:
    if "/channel/" in url:
        return url.split("/channel/")[1].split("/")[0]

    if "/@" in url:
        handle = url.split("/@")[1].split("/")[0]
        return _resolve_from_handle(handle)

    if "/c/" in url:
        name = url.split("/c/")[1].split("/")[0]
        return _resolve_from_username(name)

    raise ValueError("Unsupported YouTube URL")

def _resolve_from_handle(handle: str) -> str:
    handle = handle.replace("@", "")

    res = youtube.search().list(
        part="snippet",
        q=handle,
        type="channel",
        maxResults=1
    ).execute()

    if not res["items"]:
        raise ValueError("Channel not found")

    return res["items"][0]["snippet"]["channelId"]

def _resolve_from_username(username: str) -> str:
    res = youtube.channels().list(
        part="id",
        forUsername=username
    ).execute()

    if not res["items"]:
        raise ValueError("Channel not found")

    return res["items"][0]["id"]

# -------------------------
# FETCH CHANNEL
# -------------------------

def fetch_channel(channel_id):
    res = youtube.channels().list(
        part="snippet,statistics,brandingSettings",
        id=channel_id
    ).execute()

    if not res["items"]:
        return None

    item = res["items"][0]

    return {
        "channel_id": channel_id,
        "channel_name": item["snippet"]["title"],
        "description": item["snippet"]["description"],
        "published_at": item["snippet"]["publishedAt"],
        "country": item["brandingSettings"]["channel"].get("country"),
        "subscribers": int(item["statistics"].get("subscriberCount", 0)),
        "total_views": int(item["statistics"].get("viewCount", 0)),
        "video_count": int(item["statistics"].get("videoCount", 0)),
    }

# -------------------------
# FETCH VIDEOS
# -------------------------

def fetch_recent_videos(channel_id):
    search = youtube.search().list(
        part="id",
        channelId=channel_id,
        maxResults=MAX_VIDEOS,
        order="date",
        type="video"
    ).execute()

    ids = [i["id"]["videoId"] for i in search["items"]]

    if not ids:
        return []

    videos = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(ids)
    ).execute()

    data = []

    for v in videos["items"]:
        s = v.get("statistics", {})
        sn = v["snippet"]

        data.append({
            "video_id": v["id"],
            "title": sn["title"],
            "published_at": sn["publishedAt"],
            "views": int(s.get("viewCount", 0)),
            "likes": int(s.get("likeCount", 0)),
            "comments": int(s.get("commentCount", 0)),
            "duration": v["contentDetails"]["duration"]
        })

    return data

# -------------------------
# METRICS
# -------------------------

def calculate_channel_metrics(videos):
    if not videos:
        return {"avg_views": 0, "engagement_rate": 0, "videos_analyzed": 0}

    total_views = sum(v["views"] for v in videos)
    total_engagement = sum(v["likes"] + v["comments"] for v in videos)

    return {
        "avg_views": round(total_views / len(videos), 2),
        "engagement_rate": round((total_engagement / total_views) * 100, 2) if total_views else 0,
        "videos_analyzed": len(videos)
    }
