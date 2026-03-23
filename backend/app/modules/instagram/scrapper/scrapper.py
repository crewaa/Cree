from typing import Dict, Any
from app.modules.instagram.services.apify_client import scrape_instagram_creator

POST_LIMIT = 15


async def scrape_instagram(username: str) -> Dict[str, Any]:
    """
    Scrape Instagram profile data using Apify SDK directly.
    
    Args:
        username: Instagram username to scrape
        
    Returns:
        Dictionary with profile and posts data
        
    Raises:
        Exception: If scraping fails or profile not found
    """
    try:
        print(f"📡 Calling Apify API for @{username}...")
        raw_data = scrape_instagram_creator(username)
        print(f"✅ Apify returned data for @{username}")
        
        # Extract relevant fields from the Apify response
        # Apify field names: followersCount, followsCount, postsCount, verified, likesCount, etc.
        profile_data = {
            "username": raw_data.get("username") or raw_data.get("id") or username,
            "full_name": raw_data.get("fullName", ""),
            "bio": raw_data.get("biography", ""),
            "profile_picture": raw_data.get("profilePicUrl", ""),
            "followers": int(raw_data.get("followersCount") or raw_data.get("followers") or 0),
            "following": int(raw_data.get("followsCount") or raw_data.get("followees") or 0),
            "posts_count": int(raw_data.get("postsCount") or 0),
            "is_verified": raw_data.get("verified", False) or raw_data.get("isVerified", False),
        }
        
        # Map posts data - Apify returns latestPosts array
        posts_data = []
        posts = raw_data.get("latestPosts", []) or raw_data.get("posts", [])
        
        if posts and isinstance(posts, list):
            for post in posts[:POST_LIMIT]:
                try:
                    posts_data.append({
                        "shortcode": post.get("shortCode", "") or post.get("id", ""),
                        "likes": int(post.get("likesCount") or post.get("likeCount") or 0),
                        "comments": int(post.get("commentsCount") or 0),
                        "is_video": post.get("type") == "Video" or post.get("isVideo", False),
                        "views": int(post.get("videoViewCount")) if post.get("videoViewCount") else None,
                        "caption": post.get("caption", "") or post.get("text", ""),
                        "posted_at": post.get("timestamp") or post.get("date"),
                    })
                except (KeyError, ValueError, TypeError) as e:
                    print(f"⚠️ Error parsing post: {e}")
                    continue
        
        return {
            "profile": profile_data,
            "posts": posts_data,
        }
        
    except ValueError as e:
        raise Exception(f"Creator not found: {str(e)}")
    except Exception as e:
        raise Exception(f"Scraping error: {str(e)}")
