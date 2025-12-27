#!/usr/bin/env python3
"""Fetch data from all 5 Facebook pages and store in database."""

import json
import sqlite3
from datetime import datetime
from facebook_api import FacebookAPI, calculate_engagement_metrics


def classify_post_type(post):
    """Classify post type based on type and status_type fields."""
    post_type = post.get("type", "").lower()
    status_type = post.get("status_type", "").lower()

    if post_type == "video":
        # Check if it's a reel based on status_type or other indicators
        if "reel" in status_type:
            return "REEL"
        return "VIDEO"
    elif post_type == "photo":
        return "IMAGE"
    elif post_type == "link":
        return "LINK"
    elif status_type == "added_photos":
        return "IMAGE"
    elif status_type == "added_video":
        return "VIDEO"
    elif status_type == "shared_story":
        return "SHARE"
    else:
        return "TEXT"

# Load page tokens
with open("page_tokens.json", "r") as f:
    PAGE_TOKENS = json.load(f)

DATABASE_PATH = "data/juanbabes_analytics.db"


def init_database():
    """Initialize the database with updated schema."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Create pages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            page_id TEXT PRIMARY KEY,
            page_name TEXT NOT NULL,
            fan_count INTEGER,
            followers_count INTEGER,
            category TEXT,
            link TEXT,
            is_competitor INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    # Create posts table with enhanced fields
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            post_id TEXT PRIMARY KEY,
            page_id TEXT NOT NULL,
            message TEXT,
            created_time TEXT,
            permalink TEXT,
            post_type TEXT,
            reactions_total INTEGER DEFAULT 0,
            reactions_like INTEGER DEFAULT 0,
            reactions_love INTEGER DEFAULT 0,
            reactions_haha INTEGER DEFAULT 0,
            reactions_wow INTEGER DEFAULT 0,
            reactions_sad INTEGER DEFAULT 0,
            reactions_angry INTEGER DEFAULT 0,
            comments_count INTEGER DEFAULT 0,
            shares_count INTEGER DEFAULT 0,
            page_comments INTEGER DEFAULT 0,
            has_page_comment INTEGER DEFAULT 0,
            pes REAL DEFAULT 0,
            qes REAL DEFAULT 0,
            viral_coefficient REAL DEFAULT 0,
            total_engagement INTEGER DEFAULT 0,
            fetched_at TEXT,
            FOREIGN KEY (page_id) REFERENCES pages(page_id)
        )
    """)

    conn.commit()
    return conn


def save_page(conn, page_data):
    """Save page info to database."""
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT OR REPLACE INTO pages
        (page_id, page_name, fan_count, followers_count, category, link, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM pages WHERE page_id = ?), ?), ?)
    """, (
        page_data["page_id"],
        page_data["page_name"],
        page_data.get("fan_count"),
        page_data.get("followers_count"),
        page_data.get("category"),
        page_data.get("link"),
        page_data["page_id"],
        now,
        now
    ))
    conn.commit()


def save_post(conn, page_id, post_data):
    """Save post to database."""
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    reactions = post_data.get("reactions", {})
    metrics = post_data.get("metrics", {})

    # Use existing column names from the schema
    cursor.execute("""
        INSERT OR REPLACE INTO posts
        (post_id, page_id, title, permalink, post_type, publish_time,
         reactions_total, reactions_like, reactions_love, reactions_haha,
         reactions_wow, reactions_sad, reactions_angry,
         comments_count, shares_count, page_comments, has_page_comment,
         pes, qes, viral_coefficient, total_engagement, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post_data["post_id"],
        page_id,
        post_data.get("message", "")[:200],  # Store in title column
        post_data.get("permalink"),
        post_data.get("post_type"),
        post_data.get("created_time"),  # Store in publish_time column
        post_data.get("reactions_total", 0),
        reactions.get("like", 0),
        reactions.get("love", 0),
        reactions.get("haha", 0),
        reactions.get("wow", 0),
        reactions.get("sad", 0),
        reactions.get("angry", 0),
        post_data.get("comments_count", 0),
        post_data.get("shares_count", 0),
        post_data.get("page_comments", 0),
        1 if post_data.get("has_page_comment") else 0,
        metrics.get("pes", 0),
        metrics.get("qes", 0),
        metrics.get("viral_coefficient", 0),
        metrics.get("total_engagement", 0),
        now
    ))
    conn.commit()


def fetch_page_posts(api, page_id, page_name, days_back=90):
    """Fetch all posts from a page."""
    from datetime import timedelta
    import requests
    import time

    since_date = datetime.now() - timedelta(days=days_back)

    print(f"  Fetching posts (last {days_back} days)...")

    # Simple fields that work (no deprecated aggregated fields)
    fields = "id,message,created_time,permalink_url,shares"

    all_posts = []
    url = f"https://graph.facebook.com/v21.0/{page_id}/posts"
    params = {
        "access_token": api.access_token,
        "fields": fields,
        "limit": 100,
        "since": int(since_date.timestamp())
    }

    while True:
        try:
            resp = requests.get(url, params=params)
            data = resp.json()

            if "error" in data:
                print(f"  Error: {data['error'].get('message', 'Unknown')}")
                break

            posts = data.get("data", [])
            all_posts.extend(posts)

            # Get next page
            paging = data.get("paging", {})
            next_url = paging.get("next")

            if next_url:
                url = next_url
                params = {}  # params are in the URL
            else:
                break

            time.sleep(0.3)

        except Exception as e:
            print(f"  Error fetching posts: {e}")
            break

    print(f"  Found {len(all_posts)} posts")
    return all_posts


def process_post(api, post, page_id, fetch_details=False):
    """Process a single post to get all details."""
    import time
    import requests

    post_id = post["id"]
    shares_count = post.get("shares", {}).get("count", 0)

    # Get total reactions and comments with a single API call
    try:
        url = f"https://graph.facebook.com/v21.0/{post_id}"
        params = {
            "access_token": api.access_token,
            "fields": "reactions.summary(total_count),comments.summary(total_count)"
        }
        resp = requests.get(url, params=params)
        data = resp.json()
        total_reactions = data.get("reactions", {}).get("summary", {}).get("total_count", 0)
        comments_count = data.get("comments", {}).get("summary", {}).get("total_count", 0)
    except:
        total_reactions = 0
        comments_count = 0

    # Simplified reactions (don't get breakdown for speed)
    reactions = {"like": total_reactions, "love": 0, "haha": 0, "wow": 0, "sad": 0, "angry": 0}

    # Classify post type
    post_type = classify_post_type(post)

    # Calculate engagement metrics
    metrics = calculate_engagement_metrics({
        "reactions": reactions,
        "comments_count": comments_count,
        "shares_count": shares_count
    })

    return {
        "post_id": post_id,
        "message": post.get("message", "")[:500] if post.get("message") else "",
        "created_time": post.get("created_time"),
        "permalink": post.get("permalink_url"),
        "post_type": post_type,
        "reactions": reactions,
        "reactions_total": total_reactions,
        "comments_count": comments_count,
        "shares_count": shares_count,
        "page_comments": 0,
        "has_page_comment": False,
        "metrics": metrics
    }


def main():
    print("=" * 60)
    print("JuanBabes - Fetching Data from 5 Facebook Pages")
    print("=" * 60)

    # Initialize database
    print("\nInitializing database...")
    conn = init_database()

    total_posts = 0

    for label, data in PAGE_TOKENS.items():
        if "error" in data:
            print(f"\n[SKIP] {label} - Error: {data['error']}")
            continue

        page_id = data.get("page_id")
        page_name = data.get("page_name", label)
        token = data.get("page_access_token")

        if not token or not page_id:
            print(f"\n[SKIP] {label} - Missing token or page_id")
            continue

        print(f"\n{'='*60}")
        print(f"[{page_name}]")
        print(f"Page ID: {page_id}")
        print(f"Fans: {data.get('fan_count', 'N/A'):,}")
        print("-" * 40)

        # Save page info
        save_page(conn, data)

        # Create API client
        api = FacebookAPI(token)

        # Fetch posts
        posts = fetch_page_posts(api, page_id, page_name, days_back=90)

        # Process each post
        print(f"  Processing {len(posts)} posts...")
        for i, post in enumerate(posts):
            print(f"  Processing post {i+1}/{len(posts)}...", end="\r")
            try:
                post_data = process_post(api, post, page_id)
                save_post(conn, page_id, post_data)
                total_posts += 1
            except Exception as e:
                print(f"\n  Error processing post: {e}")

            # Rate limiting
            import time
            time.sleep(0.2)

        print(f"  Saved {len(posts)} posts to database")

    conn.close()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total pages processed: {len([p for p in PAGE_TOKENS.values() if 'page_id' in p])}")
    print(f"Total posts saved: {total_posts}")
    print(f"Database: {DATABASE_PATH}")
    print("\n[DONE] Data fetch complete!")


if __name__ == "__main__":
    main()
