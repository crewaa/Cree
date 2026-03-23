#!/usr/bin/env python3
"""
YouTube API Configuration Validator

This script validates that your YouTube API key is properly configured.
"""

import os
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.core.config import settings


def check_youtube_api_key():
    """Check if YouTube API key is configured"""
    print("\n🔑 Checking YouTube API Key Configuration...")
    
    api_key = settings.youtube_api_key
    
    if not api_key or api_key == "your_youtube_api_key_here" or api_key.startswith("AIzaSyD_your_actual"):
        print("❌ YouTube API key is not configured!")
        print("   Steps to configure:")
        print("   1. Go to https://console.cloud.google.com/")
        print("   2. Create a new project or select existing")
        print("   3. Enable 'YouTube Data API v3'")
        print("   4. Create an API Key credential")
        print("   5. Copy the key to backend/.env file:")
        print("      YOUTUBE_API_KEY=AIzaSyD...your_key...")
        return False
    
    # Validate format
    if not api_key.startswith("AIzaSy"):
        print("⚠️  API key format looks unusual (should start with 'AIzaSy')")
        print(f"   Current key: {api_key[:20]}...")
        return False
    
    print(f"✅ YouTube API key is configured")
    print(f"   Key: {api_key[:20]}...{api_key[-10:]}")
    return True


def check_apify_service():
    """Check if Apify service URL is configured"""
    print("\n🔗 Checking Apify Service Configuration...")
    
    apify_url = settings.apify_service_url
    
    if not apify_url:
        print("❌ Apify service URL is not configured!")
        return False
    
    print(f"✅ Apify service URL: {apify_url}")
    return True


def check_database_url():
    """Check if database URL is configured"""
    print("\n💾 Checking Database Configuration...")
    
    db_url = settings.database_url
    
    if not db_url:
        print("❌ Database URL is not configured!")
        return False
    
    print(f"✅ Database URL is configured")
    print(f"   URL: {db_url[:50]}...")
    return True


def main():
    """Run all checks"""
    print("=" * 60)
    print("🚀 Crewaa - Instagram & YouTube Integration Setup Validator")
    print("=" * 60)
    
    results = {
        "Database Configuration": check_database_url(),
        "YouTube API Key": check_youtube_api_key(),
        "Apify Service": check_apify_service(),
    }
    
    print("\n" + "=" * 60)
    print("📋 Configuration Summary:")
    print("=" * 60)
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check}")
    
    print("\n" + "=" * 60)
    
    all_passed = all(results.values())
    
    if all_passed:
        print("✨ All checks passed! Your system is ready to use.")
        print("\n🎉 Next steps:")
        print("   1. Make sure backend is running: uvicorn app.main:app --reload")
        print("   2. Go to http://localhost:3000/dashboard/profile")
        print("   3. Enter your Instagram and YouTube usernames")
        print("   4. Click 'Save Profile' to trigger scraping")
        print("   5. View analytics at http://localhost:3000/dashboard/analytics/influencer")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print("\n📚 For detailed setup instructions, see:")
        print("   - YOUTUBE_API_SETUP.md")
        print("   - INSTAGRAM_YOUTUBE_INTEGRATION.md")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
