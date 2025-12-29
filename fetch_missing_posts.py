#!/usr/bin/env python3
"""
Fetch missing posts from FB API that aren't in CSV data.
CSV data is prioritized (has views/reach), API ONLY fills gaps for dates NOT in CSV.
"""

import json
import sqlite3
import requests
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

DATABASE_PATH = "data/juan365_socmed.db"

# Load tokens
with open("page_tokens.json", "r") as f:
    PAGE_TOKENS = json.load(f)


def get_api_to_csv_mapping():
    """Get mapping from API page_ids to CSV page_ids."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT page_id, page_name FROM pages WHERE page_id LIKE "615%" OR page_id LIKE "100%"')
    csv_pages = {row[1]: row[0] for row in cursor.fetchall()}
    conn.close()

    mapping = {}
    for label, data in PAGE_TOKENS.items():
        api_id = data.get("page_id")
        name = data.get("page_name")
        if name in csv_pages:
            mapping[api_id] = csv_pages[name]
    return mapping


def get_csv_dates():
    """Get all dates that have CSV data (posts with views)."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT substr(publish_time, 1, 10) as date
        FROM posts
        WHERE views_count > 0
    """)
    dates = set(row[0] for row in cursor.fetchall())
    conn.close()
    return dates


def get_existing_post_ids():
    """Get all post IDs already in database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT post_id FROM posts")
    ids = set(row[0] for row in cursor.fetchall())
    conn.close()
    return ids


def fetch_posts_from_api(token, page_id, page_name, days_back=7):
    """Fetch recent posts from FB API."""
    since_date = datetime.now() - timedelta(days=days_back)
    fields = "id,message,created_time,permalink_url"

    all_posts = []
    url = f"https://graph.facebook.com/v21.0/{page_id}/posts"
    params = {
        "access_token": token,
        "fields": fields,
        "limit": 100,
        "since": int(since_date.timestamp())
    }

    while True:
        try:
            resp = requests.get(url, params=params)
            data = resp.json()

            if "error" in data:
                print(f"  [{page_name}] API Error: {data['error'].get('message', 'Unknown')}")
                break

            posts = data.get("data", [])
            all_posts.extend(posts)

            paging = data.get("paging", {})
            next_url = paging.get("next")

            if next_url:
                url = next_url
                params = {}
            else:
                break

            time.sleep(0.1)
        except Exception as e:
            print(f"  [{page_name}] Error: {e}")
            break

    return all_posts


def get_post_details(token, post_id):
    """Get reactions, comments, shares for a post."""
    try:
        url = f"https://graph.facebook.com/v21.0/{post_id}"
        params = {
            "access_token": token,
            "fields": "reactions.summary(total_count),comments.summary(total_count),shares,attachments{media_type}"
        }
        resp = requests.get(url, params=params)
        data = resp.json()

        reactions = data.get("reactions", {}).get("summary", {}).get("total_count", 0)
        comments = data.get("comments", {}).get("summary", {}).get("total_count", 0)
        shares = data.get("shares", {}).get("count", 0)

        attachments = data.get("attachments", {}).get("data", [])
        if attachments:
            media_type = attachments[0].get("media_type", "").lower()
            if media_type == "video":
                post_type = "Videos"
            elif media_type == "photo":
                post_type = "Photos"
            else:
                post_type = "Text"
        else:
            post_type = "Text"

        return reactions, comments, shares, post_type
    except:
        return 0, 0, 0, "Text"


def save_post(conn, page_id, post_id, post_data, reactions, comments, shares, post_type):
    """Save a post to database."""
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    total_engagement = reactions + comments + shares
    pes = (reactions * 1.0) + (comments * 2.0) + (shares * 3.0)

    cursor.execute("""
        INSERT OR IGNORE INTO posts
        (post_id, page_id, title, permalink, post_type, publish_time,
         reactions_total, comments_count, shares_count,
         pes, total_engagement, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post_id,
        page_id,
        (post_data.get("message", "") or "")[:200],
        post_data.get("permalink_url"),
        post_type,
        post_data.get("created_time"),
        reactions,
        comments,
        shares,
        pes,
        total_engagement,
        now
    ))
    return cursor.rowcount > 0


def main():
    print("=" * 60)
    print("Fetching Missing Posts from FB API")
    print("(API ONLY for dates NOT in CSV)")
    print("=" * 60)

    # Get dates that have CSV data
    csv_dates = get_csv_dates()
    print(f"\nDates with CSV data: {len(csv_dates)}")
    if csv_dates:
        print(f"  CSV range: {min(csv_dates)} to {max(csv_dates)}")

    # Get existing post IDs
    existing_ids = get_existing_post_ids()
    print(f"Existing posts in database: {len(existing_ids)}")

    # Get API to CSV page_id mapping
    api_to_csv = get_api_to_csv_mapping()
    print(f"Page ID mappings: {len(api_to_csv)}")

    conn = sqlite3.connect(DATABASE_PATH)
    total_new = 0
    total_skipped = 0

    for label, data in PAGE_TOKENS.items():
        api_page_id = data.get("page_id")
        page_name = data.get("page_name", label)
        token = data.get("page_access_token")

        if not token or not api_page_id:
            continue

        db_page_id = api_to_csv.get(api_page_id, api_page_id)

        print(f"\n[{page_name}] Fetching recent posts...")

        posts = fetch_posts_from_api(token, api_page_id, page_name, days_back=7)
        print(f"  Found {len(posts)} posts from API")

        # Filter to only new posts NOT in database
        new_posts = [p for p in posts if p["id"] not in existing_ids]
        print(f"  New posts not in database: {len(new_posts)}")

        # Save only posts from dates NOT in CSV
        page_new = 0
        page_skipped = 0
        for post in new_posts:
            post_id = post["id"]
            created_time = post.get("created_time", "")
            post_date = created_time[:10] if created_time else ""

            # SKIP if this date has CSV data
            if post_date in csv_dates:
                page_skipped += 1
                continue

            reactions, comments, shares, post_type = get_post_details(token, post_id)

            if save_post(conn, db_page_id, post_id, post, reactions, comments, shares, post_type):
                page_new += 1
                print(f"  + Added ({post_date}): {post_id[:25]}...")

            time.sleep(0.2)

        total_new += page_new
        total_skipped += page_skipped
        if page_skipped > 0:
            print(f"  Skipped {page_skipped} posts (dates covered by CSV)")

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print(f"DONE! Added {total_new} new posts from API")
    print(f"Skipped {total_skipped} posts (dates already in CSV)")
    print("=" * 60)


if __name__ == "__main__":
    main()
