#!/usr/bin/env python3
"""
Full Month Sync - Sync all posts for a month from Facebook API to database.

This script fetches ALL posts for a specified month from the Facebook API
and syncs them to the database, ensuring DB matches API exactly.

Usage:
    python full_month_sync.py                    # Sync current month
    python full_month_sync.py --month 2026-01    # Sync specific month
    python full_month_sync.py --project juanbabes --month 2026-01
    python full_month_sync.py --all-projects     # Sync all 3 projects
"""

import os
import sys
import json
import sqlite3
import argparse
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Facebook Graph API settings
GRAPH_API_VERSION = "v18.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

# Project configurations
PROJECTS = {
    "juanstudio": {
        "dir": r"C:\Users\us\Desktop\juanstudio_project",
        "db": r"C:\Users\us\Desktop\juanstudio_project\data\juanstudio_analytics.db",
        "name": "JuanStudio"
    },
    "juanbabes": {
        "dir": r"C:\Users\us\Desktop\juanbabes_project",
        "db": r"C:\Users\us\Desktop\juanbabes_project\data\juanbabes_analytics.db",
        "name": "JuanBabes"
    },
    "juan365": {
        "dir": r"C:\Users\us\Desktop\juan365_socmed_report",
        "db": r"C:\Users\us\Desktop\juan365_socmed_report\data\juan365_socmed.db",
        "name": "Juan365"
    }
}


def load_tokens(project_dir: str) -> dict:
    """Load page access tokens from project's page_tokens.json."""
    tokens_path = os.path.join(project_dir, "page_tokens.json")
    if not os.path.exists(tokens_path):
        return {}
    with open(tokens_path, 'r') as f:
        return json.load(f)


def fetch_all_posts_for_month(tokens: dict, year: int, month: int) -> list:
    """Fetch ALL posts from Facebook API for a specific month."""
    all_posts = []

    # Create UTC timestamps for the month
    month_start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        month_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        month_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

    month_str = f"{year}-{month:02d}"

    # Extended fields to get full engagement data
    fields = [
        "id", "message", "created_time", "permalink_url",
        "shares", "reactions.summary(true)", "comments.summary(true)",
        "attachments{type,media_type}"
    ]

    for page_name, page_data in tokens.items():
        page_id = page_data.get("page_id")
        token = page_data.get("page_access_token") or page_data.get("token")
        if not token or not page_id:
            continue

        print(f"    Fetching {page_name}...")

        url = f"{GRAPH_API_BASE}/{page_id}/posts"
        params = {
            "access_token": token,
            "fields": ",".join(fields),
            "since": int(month_start.timestamp()),
            "until": int(month_end.timestamp()),
            "limit": 100
        }

        page_posts = []

        while url:
            try:
                response = requests.get(url, params=params, timeout=30)
                data = response.json()

                if "error" in data:
                    print(f"      API error: {data['error'].get('message', 'Unknown')}")
                    break

                posts = data.get("data", [])
                for post in posts:
                    created = post.get("created_time", "")[:7]  # YYYY-MM
                    if created == month_str:
                        # Extract post_id (API returns "pageid_postid" format)
                        full_id = post.get("id", "")
                        post_id = full_id.split("_")[-1] if "_" in full_id else full_id

                        # Get metrics
                        reactions = post.get("reactions", {}).get("summary", {}).get("total_count", 0)
                        comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
                        shares = post.get("shares", {}).get("count", 0)

                        # Determine post type from attachments
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

                        page_posts.append({
                            "post_id": post_id,
                            "page_id": page_id,
                            "title": (post.get("message", "") or "")[:200],
                            "permalink": post.get("permalink_url", ""),
                            "post_type": post_type,
                            "publish_time": post.get("created_time", ""),
                            "reactions_total": reactions,
                            "comments_count": comments,
                            "shares_count": shares,
                            "total_engagement": reactions + comments + shares,
                            "pes": (reactions * 1.0) + (comments * 2.0) + (shares * 3.0)
                        })

                # Handle pagination
                paging = data.get("paging", {})
                url = paging.get("next")
                params = {}  # Params included in next URL

            except Exception as e:
                print(f"      Request error: {e}")
                break

        print(f"      Found {len(page_posts)} posts")
        all_posts.extend(page_posts)

    return all_posts


def sync_month_to_db(db_path: str, year: int, month: int, api_posts: list) -> dict:
    """
    Sync a month's data from API to database.
    - Delete posts in DB that are NOT in API (for the month only)
    - Update/insert posts from API with latest engagement data
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    month_str = f"{year}-{month:02d}"

    # Get API post IDs
    api_post_ids = set(p["post_id"] for p in api_posts)

    # Get DB post IDs for the month
    cursor.execute("""
        SELECT post_id FROM posts
        WHERE substr(publish_time, 1, 7) = ?
    """, (month_str,))
    db_post_ids = set(row[0] for row in cursor.fetchall())

    # Delete posts that are in DB but NOT in API (for this month only)
    posts_to_delete = db_post_ids - api_post_ids
    deleted = 0
    if posts_to_delete:
        print(f"    Removing {len(posts_to_delete)} posts not in API...")
        for post_id in posts_to_delete:
            cursor.execute("DELETE FROM posts WHERE post_id = ?", (post_id,))
            deleted += 1

    # Update/insert posts from API
    updated = 0
    inserted = 0
    for post in api_posts:
        # Check if post exists
        cursor.execute("SELECT post_id FROM posts WHERE post_id = ?", (post["post_id"],))
        exists = cursor.fetchone()

        if exists:
            # Update with latest engagement data
            cursor.execute("""
                UPDATE posts SET
                    title = ?,
                    permalink = ?,
                    post_type = ?,
                    reactions_total = ?,
                    comments_count = ?,
                    shares_count = ?,
                    total_engagement = ?,
                    pes = ?,
                    fetched_at = ?
                WHERE post_id = ?
            """, (
                post["title"],
                post["permalink"],
                post["post_type"],
                post["reactions_total"],
                post["comments_count"],
                post["shares_count"],
                post["total_engagement"],
                post["pes"],
                datetime.now().isoformat(),
                post["post_id"]
            ))
            updated += 1
        else:
            # Insert new post
            cursor.execute("""
                INSERT INTO posts
                (post_id, page_id, title, permalink, post_type, publish_time,
                 reactions_total, comments_count, shares_count, total_engagement,
                 pes, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post["post_id"],
                post["page_id"],
                post["title"],
                post["permalink"],
                post["post_type"],
                post["publish_time"],
                post["reactions_total"],
                post["comments_count"],
                post["shares_count"],
                post["total_engagement"],
                post["pes"],
                datetime.now().isoformat()
            ))
            inserted += 1

    conn.commit()
    conn.close()

    return {
        "api_posts": len(api_posts),
        "db_before": len(db_post_ids),
        "deleted": deleted,
        "updated": updated,
        "inserted": inserted
    }


def sync_project(project_key: str, year: int, month: int) -> dict:
    """Sync a single project for a specific month."""
    config = PROJECTS[project_key]

    print(f"\n{'='*60}")
    print(f"Syncing {config['name']} for {year}-{month:02d}")
    print(f"{'='*60}")

    # Load tokens
    tokens = load_tokens(config["dir"])
    if not tokens:
        print(f"  [X] No tokens found in {config['dir']}")
        return None

    print(f"  Found {len(tokens)} pages")

    # Fetch all posts for the month
    print(f"\n  Fetching posts from API...")
    api_posts = fetch_all_posts_for_month(tokens, year, month)
    print(f"\n  Total posts from API: {len(api_posts)}")

    if not api_posts:
        print(f"  [!] No posts found for {year}-{month:02d}")
        return {"api_posts": 0, "deleted": 0, "updated": 0, "inserted": 0}

    # Sync to database
    print(f"\n  Syncing to database...")
    result = sync_month_to_db(config["db"], year, month, api_posts)

    print(f"\n  Sync complete:")
    print(f"    API posts:  {result['api_posts']}")
    print(f"    DB before:  {result['db_before']}")
    print(f"    Deleted:    {result['deleted']}")
    print(f"    Updated:    {result['updated']}")
    print(f"    Inserted:   {result['inserted']}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Full month sync from Facebook API")
    parser.add_argument("--project", choices=["juanstudio", "juanbabes", "juan365"],
                        default="juanstudio", help="Project to sync")
    parser.add_argument("--month", help="Month to sync (YYYY-MM), default: current month")
    parser.add_argument("--all-projects", action="store_true", help="Sync all 3 projects")
    args = parser.parse_args()

    # Parse month
    if args.month:
        try:
            year, month = map(int, args.month.split("-"))
        except:
            print(f"Invalid month format: {args.month}. Use YYYY-MM")
            sys.exit(1)
    else:
        now = datetime.now()
        year, month = now.year, now.month

    print(f"\n{'#'*60}")
    print(f"  FULL MONTH SYNC - {year}-{month:02d}")
    print(f"{'#'*60}")

    if args.all_projects:
        projects = ["juanstudio", "juanbabes", "juan365"]
    else:
        projects = [args.project]

    results = {}
    for project in projects:
        result = sync_project(project, year, month)
        results[project] = result

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for project, result in results.items():
        if result:
            print(f"  {project}: {result['api_posts']} posts synced "
                  f"(+{result['inserted']} new, {result['updated']} updated, -{result['deleted']} removed)")
        else:
            print(f"  {project}: FAILED")

    print(f"\n[OK] Full month sync complete!")
    print(f"\nNext steps:")
    print(f"  1. Run export_static_data.py to update JSON")
    print(f"  2. Git push to deploy to Vercel")


if __name__ == "__main__":
    main()
