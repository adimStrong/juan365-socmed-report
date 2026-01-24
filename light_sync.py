#!/usr/bin/env python3
"""
Light Facebook API Sync - Fetches only last 2 days with rate limit protection.

This is a gentler version of scheduled_sync.py designed to avoid rate limits.
- Only fetches last 2 days (instead of 30)
- Smaller batch size (25 instead of 100)
- Delay between pages (3 seconds)
- Only INSERTS new posts (doesn't overwrite existing)

Usage:
    python light_sync.py              # Sync last 2 days
    python light_sync.py --days 3     # Sync last 3 days
"""

import json
import sqlite3
import requests
from datetime import datetime, timedelta
import os
import sys
import time

# Configuration
DATABASE_PATH = "data/juan365_socmed.db"
TOKENS_FILE = "page_tokens.json"
GRAPH_API_VERSION = "v18.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

# Light sync settings
DEFAULT_DAYS = 2
BATCH_SIZE = 25  # Smaller batch to avoid rate limits
DELAY_BETWEEN_PAGES = 3  # Seconds to wait between pages

# Page ID mapping: API (old) -> CSV (new) format
# This ensures posts are stored with the same page_id as CSV imports
PAGE_ID_MAP = {
    '580104038511364': '61572881214141',      # Juan365
    '481447078389174': '61569634500241',      # Juan365 Live Stream
    '708878528972997': '61578179424678',      # Juan365 Studios
    '101968408687724': '100069911784904',     # JuanBingo
    '839729525890738': '61582036535912',      # JuanSports
    '718958694640884': '61579361702713',      # Juan365 Cares
}

# Minimal fields to reduce data size
POST_FIELDS = [
    "id", "message", "created_time", "permalink_url",
    "shares", "reactions.summary(true)", "comments.summary(true)",
    "attachments{type,media_type}"
]


def load_tokens():
    """Load page access tokens from JSON file."""
    if not os.path.exists(TOKENS_FILE):
        print(f"[X] Token file not found: {TOKENS_FILE}")
        return None
    with open(TOKENS_FILE, 'r') as f:
        return json.load(f)


def fetch_page_posts_light(page_id, token, days=2):
    """Fetch posts with rate limit protection."""
    since = datetime.now() - timedelta(days=days)
    since_ts = int(since.timestamp())

    url = f"{GRAPH_API_BASE}/{page_id}/posts"
    params = {
        "access_token": token,
        "fields": ",".join(POST_FIELDS),
        "since": since_ts,
        "limit": BATCH_SIZE  # Smaller limit
    }

    posts = []
    page_count = 0
    max_pages = 3  # Limit pagination to avoid too many requests

    while url and page_count < max_pages:
        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()

            if "error" in data:
                error_msg = data['error'].get('message', 'Unknown')
                if "reduce the amount of data" in error_msg.lower():
                    print(f"    [!] Rate limited - skipping")
                else:
                    print(f"    [X] API Error: {error_msg}")
                break

            batch = data.get("data", [])
            posts.extend(batch)
            page_count += 1

            # Check for more pages
            paging = data.get("paging", {})
            url = paging.get("next")
            params = {}

            if url and page_count < max_pages:
                time.sleep(1)  # Small delay between pagination

        except requests.exceptions.Timeout:
            print(f"    [!] Request timeout")
            break
        except Exception as e:
            print(f"    [X] Error: {e}")
            break

    return posts


def save_posts_to_db(page_id, page_name, posts):
    """Save posts - only INSERT new ones, don't replace existing."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Convert page_id to CSV format (new IDs) for consistency
    csv_page_id = PAGE_ID_MAP.get(page_id, page_id)

    # Ensure page exists with CSV-format page_id
    cursor.execute("""
        INSERT OR IGNORE INTO pages (page_id, page_name, created_at, updated_at)
        VALUES (?, ?, ?, ?)
    """, (csv_page_id, page_name, datetime.now().isoformat(), datetime.now().isoformat()))

    new_count = 0
    updated_count = 0

    for post in posts:
        post_id = post.get("id", "").split("_")[-1]
        if not post_id:
            continue

        # Check if post already exists
        cursor.execute("SELECT post_id FROM posts WHERE post_id = ?", (post_id,))
        exists = cursor.fetchone()

        message = post.get("message", "")[:200] if post.get("message") else ""
        permalink = post.get("permalink_url", "")
        created_time = post.get("created_time", "")

        # Convert created_time to PH timezone format
        if created_time:
            try:
                dt = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                # Convert to PH time (UTC+8)
                dt_ph = dt + timedelta(hours=8)
                created_time = dt_ph.strftime('%Y-%m-%dT%H:%M:%S')
            except:
                pass

        # Get post type
        attachments = post.get("attachments", {}).get("data", [])
        post_type = "Text"
        if attachments:
            media_type = attachments[0].get("media_type", "")
            attach_type = attachments[0].get("type", "")
            if media_type == "video" or attach_type == "video_inline":
                post_type = "Videos"
            elif media_type == "photo" or attach_type == "photo":
                post_type = "Photos"
            elif "reel" in str(attachments).lower():
                post_type = "Reels"

        # Get metrics
        reactions = post.get("reactions", {}).get("summary", {}).get("total_count", 0)
        comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
        shares = post.get("shares", {}).get("count", 0)
        total_engagement = reactions + comments + shares

        if exists:
            # Update metrics only for existing posts
            cursor.execute("""
                UPDATE posts SET
                    reactions_total = ?,
                    comments_count = ?,
                    shares_count = ?,
                    total_engagement = ?,
                    fetched_at = ?
                WHERE post_id = ?
            """, (reactions, comments, shares, total_engagement,
                  datetime.now().isoformat(), post_id))
            updated_count += 1
        else:
            # Insert new post (use csv_page_id for consistency with CSV imports)
            cursor.execute("""
                INSERT INTO posts
                (post_id, page_id, title, permalink, post_type, publish_time,
                 reactions_total, comments_count, shares_count, total_engagement, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (post_id, csv_page_id, message, permalink, post_type, created_time,
                  reactions, comments, shares, total_engagement,
                  datetime.now().isoformat()))
            new_count += 1

    conn.commit()
    conn.close()

    return new_count, updated_count


def run_light_sync(days=2):
    """Run light sync."""
    print("=" * 60)
    print("Light Facebook API Sync (Rate Limit Safe)")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Fetching: Last {days} days | Batch: {BATCH_SIZE} posts")
    print("=" * 60)

    tokens = load_tokens()
    if not tokens:
        return False

    print(f"\nFound {len(tokens)} pages\n")

    total_new = 0
    total_updated = 0

    for i, (page_key, page_data) in enumerate(tokens.items()):
        page_id = page_data.get("page_id", page_key)
        token = page_data.get("page_access_token") or page_data.get("token")
        name = page_data.get("page_name") or page_data.get("name", f"Page {page_key}")

        if not token:
            print(f"[X] {name}: No token")
            continue

        print(f"[{i+1}/{len(tokens)}] {name}")
        print(f"    Fetching last {days} days...")

        posts = fetch_page_posts_light(page_id, token, days=days)

        if posts:
            new_count, updated_count = save_posts_to_db(page_id, name, posts)
            print(f"    [OK] {new_count} new, {updated_count} updated")
            total_new += new_count
            total_updated += updated_count
        else:
            print(f"    No posts found")

        # Delay between pages to avoid rate limits
        if i < len(tokens) - 1:
            print(f"    Waiting {DELAY_BETWEEN_PAGES}s...")
            time.sleep(DELAY_BETWEEN_PAGES)

    print(f"\n{'=' * 60}")
    print(f"SYNC COMPLETE")
    print(f"  New posts: {total_new}")
    print(f"  Updated: {total_updated}")
    print("=" * 60)

    return True


def main():
    days = DEFAULT_DAYS

    # Parse --days argument
    for i, arg in enumerate(sys.argv):
        if arg == "--days" and i + 1 < len(sys.argv):
            try:
                days = int(sys.argv[i + 1])
            except ValueError:
                pass

    run_light_sync(days=days)


if __name__ == "__main__":
    main()
