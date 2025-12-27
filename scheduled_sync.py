#!/usr/bin/env python3
"""
Scheduled Facebook API Sync for JuanBabes Analytics

This script fetches the latest posts from Facebook Pages using the Graph API.
Can be run manually or scheduled via Windows Task Scheduler / cron.

Requirements:
- Valid Facebook Page Access Tokens (60-day expiry, stored in page_tokens.json)
- Pages must be managed by you or your business

Usage:
    python scheduled_sync.py           # Run sync
    python scheduled_sync.py --check   # Check token status only

Schedule with Windows Task Scheduler:
1. Open Task Scheduler
2. Create Basic Task → "JuanBabes Daily Sync"
3. Trigger: Daily at 6:00 AM
4. Action: Start Program
   - Program: python
   - Arguments: C:\Users\us\Desktop\juanbabes_project\scheduled_sync.py
   - Start in: C:\Users\us\Desktop\juanbabes_project

Or with cron (Linux/Mac):
    0 6 * * * cd /path/to/project && python scheduled_sync.py >> sync.log 2>&1
"""

import json
import sqlite3
import requests
from datetime import datetime, timedelta
import os
import sys

# Configuration
DATABASE_PATH = "data/juanbabes_analytics.db"
TOKENS_FILE = "page_tokens.json"
GRAPH_API_VERSION = "v18.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

# Fields to fetch from API
POST_FIELDS = [
    "id", "message", "created_time", "permalink_url",
    "shares", "reactions.summary(true)", "comments.summary(true)",
    "attachments{type,media_type}"
]


def load_tokens():
    """Load page access tokens from JSON file."""
    if not os.path.exists(TOKENS_FILE):
        print(f"❌ Token file not found: {TOKENS_FILE}")
        print("   Create page_tokens.json with format:")
        print('   {"PAGE_ID": {"token": "ACCESS_TOKEN", "name": "Page Name"}}')
        return None

    with open(TOKENS_FILE, 'r') as f:
        return json.load(f)


def check_token_validity(page_id, token):
    """Check if a token is still valid."""
    url = f"{GRAPH_API_BASE}/debug_token"
    params = {"input_token": token, "access_token": token}

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if "data" in data:
            is_valid = data["data"].get("is_valid", False)
            expires_at = data["data"].get("expires_at", 0)

            if expires_at:
                expiry = datetime.fromtimestamp(expires_at)
                days_left = (expiry - datetime.now()).days
                return is_valid, days_left

            return is_valid, None
        return False, None
    except:
        return False, None


def fetch_page_posts(page_id, token, days=7):
    """Fetch posts from a page for the last N days."""
    since = datetime.now() - timedelta(days=days)
    since_ts = int(since.timestamp())

    url = f"{GRAPH_API_BASE}/{page_id}/posts"
    params = {
        "access_token": token,
        "fields": ",".join(POST_FIELDS),
        "since": since_ts,
        "limit": 100
    }

    posts = []

    while url:
        try:
            response = requests.get(url, params=params)
            data = response.json()

            if "error" in data:
                print(f"  ❌ API Error: {data['error'].get('message', 'Unknown')}")
                break

            posts.extend(data.get("data", []))

            # Handle pagination
            paging = data.get("paging", {})
            url = paging.get("next")
            params = {}  # Params are included in the next URL

        except Exception as e:
            print(f"  ❌ Request error: {e}")
            break

    return posts


def save_posts_to_db(page_id, page_name, posts):
    """Save fetched posts to the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Ensure page exists
    cursor.execute("""
        INSERT OR IGNORE INTO pages (page_id, page_name, created_at, updated_at)
        VALUES (?, ?, ?, ?)
    """, (page_id, page_name, datetime.now().isoformat(), datetime.now().isoformat()))

    saved = 0

    for post in posts:
        post_id = post.get("id", "").split("_")[-1]  # Extract post ID
        if not post_id:
            continue

        message = post.get("message", "")[:200]
        permalink = post.get("permalink_url", "")
        created_time = post.get("created_time", "")

        # Get post type from attachments
        attachments = post.get("attachments", {}).get("data", [])
        post_type = "Text"
        if attachments:
            media_type = attachments[0].get("media_type", "")
            attach_type = attachments[0].get("type", "")

            if media_type == "video" or attach_type == "video_inline":
                post_type = "Videos"
            elif media_type == "photo" or attach_type == "photo":
                post_type = "Photos"
            elif attach_type == "native_templates" and "reel" in str(attachments).lower():
                post_type = "Reels"

        # Get metrics
        reactions = post.get("reactions", {}).get("summary", {}).get("total_count", 0)
        comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
        shares = post.get("shares", {}).get("count", 0)

        total_engagement = reactions + comments + shares
        pes = (reactions * 1.0) + (comments * 2.0) + (shares * 3.0)

        cursor.execute("""
            INSERT OR REPLACE INTO posts
            (post_id, page_id, title, permalink, post_type, publish_time,
             reactions_total, comments_count, shares_count,
             pes, total_engagement, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post_id, page_id, message, permalink, post_type, created_time,
            reactions, comments, shares, pes, total_engagement,
            datetime.now().isoformat()
        ))
        saved += 1

    conn.commit()
    conn.close()

    return saved


def run_sync(check_only=False):
    """Main sync function."""
    print("=" * 60)
    print("JuanBabes Facebook API Sync")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    tokens = load_tokens()
    if not tokens:
        return False

    print(f"\nFound {len(tokens)} pages to sync:\n")

    all_valid = True
    total_posts = 0

    for page_id, page_data in tokens.items():
        token = page_data.get("token")
        name = page_data.get("name", f"Page {page_id}")

        # Check token validity
        is_valid, days_left = check_token_validity(page_id, token)

        if not is_valid:
            print(f"❌ {name}: Token INVALID or expired")
            all_valid = False
            continue

        status = "✅" if days_left and days_left > 14 else "⚠️"
        days_msg = f"{days_left} days left" if days_left else "No expiry"
        print(f"{status} {name} ({page_id}): Token valid - {days_msg}")

        if days_left and days_left <= 14:
            print(f"   ⚠️  Token expires soon! Refresh at:")
            print(f"   https://business.facebook.com/settings/pages")

        if check_only:
            continue

        # Fetch and save posts
        print(f"   Fetching posts...")
        posts = fetch_page_posts(page_id, token, days=7)

        if posts:
            saved = save_posts_to_db(page_id, name, posts)
            print(f"   ✅ Saved {saved} posts")
            total_posts += saved
        else:
            print(f"   No new posts found")

    if not check_only:
        print(f"\n{'=' * 60}")
        print(f"SYNC COMPLETE: {total_posts} posts updated")
        print("=" * 60)

    return all_valid


def main():
    check_only = "--check" in sys.argv

    if check_only:
        print("\n🔍 Token check mode (no sync)\n")

    success = run_sync(check_only=check_only)

    if not success:
        print("\n⚠️  Some tokens need attention!")
        print("   To refresh tokens:")
        print("   1. Go to https://business.facebook.com/settings/pages")
        print("   2. Select each page → Generate new token")
        print("   3. Update page_tokens.json")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
