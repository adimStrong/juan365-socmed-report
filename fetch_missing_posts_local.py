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

# Telegram notifications
try:
    from telegram_notifier import send_new_post_alert
    TELEGRAM_ENABLED = True
except ImportError:
    TELEGRAM_ENABLED = False
    print("Warning: telegram_notifier not found, notifications disabled")

DATABASE_PATH = "data/juan365_socmed.db"

# Load tokens
with open("page_tokens.json", "r") as f:
    PAGE_TOKENS = json.load(f)


def get_db_page_ids():
    """Get page_ids that exist in the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT page_id FROM pages')
    page_ids = set(row[0] for row in cursor.fetchall())
    conn.close()
    return page_ids


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
            "fields": "reactions.summary(total_count),comments.summary(total_count),shares,attachments{media_type,target{id}}"
        }
        resp = requests.get(url, params=params)
        data = resp.json()

        reactions = data.get("reactions", {}).get("summary", {}).get("total_count", 0)
        comments = data.get("comments", {}).get("summary", {}).get("total_count", 0)
        shares = data.get("shares", {}).get("count", 0)

        attachments = data.get("attachments", {}).get("data", [])
        video_id = None
        if attachments:
            media_type = attachments[0].get("media_type", "").lower()
            if media_type == "video":
                post_type = "Videos"
                # Get video ID for fetching video insights
                target = attachments[0].get("target", {})
                video_id = target.get("id")
            elif media_type == "photo":
                post_type = "Photos"
            else:
                post_type = "Text"
        else:
            post_type = "Text"

        return reactions, comments, shares, post_type, video_id
    except:
        return 0, 0, 0, "Text", None


def get_video_insights(token, video_id):
    """Get video watch time metrics."""
    if not video_id:
        return {}

    try:
        url = f"https://graph.facebook.com/v21.0/{video_id}/video_insights"
        params = {
            "access_token": token,
            "metric": ",".join([
                "total_video_views",
                "total_video_avg_time_watched",
                "total_video_complete_views",
                "total_video_10s_views",
                "total_video_30s_views"
            ])
        }
        resp = requests.get(url, params=params)
        data = resp.json()

        if "error" in data:
            return {}

        insights = {}
        for item in data.get("data", []):
            name = item.get("name", "")
            values = item.get("values", [{}])
            if values:
                insights[name] = values[0].get("value", 0)

        return {
            "avg_watch_time_ms": insights.get("total_video_avg_time_watched", 0),
            "video_views_3sec": insights.get("total_video_views", 0),
            "video_views_complete": insights.get("total_video_complete_views", 0),
            "video_views_10sec": insights.get("total_video_10s_views", 0),
            "video_views_30sec": insights.get("total_video_30s_views", 0)
        }
    except Exception as e:
        return {}


def save_post(conn, page_id, post_id, post_data, reactions, comments, shares, post_type, video_insights=None):
    """Save a NEW post to database with optional video insights."""
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    total_engagement = reactions + comments + shares
    pes = (reactions * 1.0) + (comments * 2.0) + (shares * 3.0)

    # Extract video metrics if available
    avg_watch_time_ms = 0
    video_views_3sec = 0
    video_views_complete = 0
    watch_completion_rate = 0

    if video_insights:
        avg_watch_time_ms = video_insights.get("avg_watch_time_ms", 0)
        video_views_3sec = video_insights.get("video_views_3sec", 0)
        video_views_complete = video_insights.get("video_views_complete", 0)
        if video_views_3sec > 0:
            watch_completion_rate = round(video_views_complete / video_views_3sec * 100, 2)

    cursor.execute("""
        INSERT OR IGNORE INTO posts
        (post_id, page_id, title, permalink, post_type, publish_time,
         reactions_total, comments_count, shares_count,
         pes, total_engagement, fetched_at,
         avg_watch_time_ms, video_views_3sec, video_views_complete, watch_completion_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        now,
        avg_watch_time_ms,
        video_views_3sec,
        video_views_complete,
        watch_completion_rate
    ))
    return cursor.rowcount > 0


def update_post_engagement(conn, post_id, reactions, comments, shares):
    """Update engagement data for existing API posts (no views/reach)."""
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    total_engagement = reactions + comments + shares
    pes = (reactions * 1.0) + (comments * 2.0) + (shares * 3.0)

    # Only update posts that have NO views data (API posts, not CSV)
    cursor.execute("""
        UPDATE posts
        SET reactions_total = ?,
            comments_count = ?,
            shares_count = ?,
            pes = ?,
            total_engagement = ?,
            fetched_at = ?
        WHERE post_id = ?
        AND (views_count IS NULL OR views_count = 0)
    """, (reactions, comments, shares, pes, total_engagement, now, post_id))
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

    # Get valid page IDs from database
    db_page_ids = get_db_page_ids()
    print(f"Pages in database: {len(db_page_ids)}")

    conn = sqlite3.connect(DATABASE_PATH)
    total_new = 0
    total_skipped = 0

    for label, data in PAGE_TOKENS.items():
        page_id = data.get("page_id")
        page_name = data.get("page_name", label)
        token = data.get("page_access_token")

        if not token or not page_id:
            continue

        # Use page_id directly (must match database)
        db_page_id = page_id

        print(f"\n[{page_name}] Fetching recent posts...")

        posts = fetch_posts_from_api(token, page_id, page_name, days_back=7)
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

            reactions, comments, shares, post_type, video_id = get_post_details(token, post_id)

            # Fetch video insights if this is a video post
            video_insights = None
            if video_id and post_type == "Videos":
                video_insights = get_video_insights(token, video_id)
                time.sleep(0.1)  # Rate limiting for video insights

            if save_post(conn, db_page_id, post_id, post, reactions, comments, shares, post_type, video_insights):
                page_new += 1
                video_info = ""
                if video_insights and video_insights.get("avg_watch_time_ms"):
                    avg_sec = video_insights["avg_watch_time_ms"] / 1000
                    video_info = f" [avg watch: {avg_sec:.1f}s]"
                print(f"  + Added ({post_date}): {post_id[:25]}...{video_info}")

                # Send Telegram notification for new post
                if TELEGRAM_ENABLED:
                    try:
                        send_new_post_alert(
                            page_name=page_name,
                            post_type=post_type,
                            title=post.get("message", ""),
                            permalink=post.get("permalink_url", ""),
                            publish_time=created_time
                        )
                        print(f"  -> Telegram alert sent!")
                    except Exception as e:
                        print(f"  -> Telegram error: {e}")

            time.sleep(0.2)

        # Update existing API posts (refresh engagement data)
        existing_posts = [p for p in posts if p["id"] in existing_ids]
        page_updated = 0
        for post in existing_posts:
            post_id = post["id"]
            reactions, comments, shares, post_type, video_id = get_post_details(token, post_id)
            if update_post_engagement(conn, post_id, reactions, comments, shares):
                page_updated += 1
            time.sleep(0.1)

        if page_updated > 0:
            print(f"  ~ Updated {page_updated} existing posts")

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
