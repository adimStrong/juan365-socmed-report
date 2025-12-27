#!/usr/bin/env python3
"""Fetch data from a single Facebook page - simpler, faster approach."""

import json
import sqlite3
import requests
import time
from datetime import datetime

# Load page tokens
with open("page_tokens.json", "r") as f:
    PAGE_TOKENS = json.load(f)

DATABASE_PATH = "data/juan365_socmed.db"
START_DATE = "2025-10-01"  # Start from October 2025


def get_conn():
    return sqlite3.connect(DATABASE_PATH)


def save_page(page_data):
    """Save page info to database."""
    conn = get_conn()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT OR REPLACE INTO pages
        (page_id, page_name, fan_count, followers_count, created_at, updated_at)
        VALUES (?, ?, ?, ?, COALESCE((SELECT created_at FROM pages WHERE page_id = ?), ?), ?)
    """, (
        page_data["page_id"],
        page_data["page_name"],
        page_data.get("fan_count"),
        page_data.get("followers_count"),
        page_data["page_id"],
        now,
        now
    ))
    conn.commit()
    conn.close()


def save_post(page_id, post_data):
    """Save post to database."""
    conn = get_conn()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT OR REPLACE INTO posts
        (post_id, page_id, title, permalink, post_type, publish_time,
         reactions_total, comments_count, shares_count,
         pes, qes, viral_coefficient, total_engagement, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post_data["post_id"],
        page_id,
        post_data.get("message", "")[:200],
        post_data.get("permalink"),
        post_data.get("post_type", "TEXT"),
        post_data.get("created_time"),
        post_data.get("reactions", 0),
        post_data.get("comments", 0),
        post_data.get("shares", 0),
        post_data.get("pes", 0),
        0,  # qes
        0,  # viral coefficient
        post_data.get("engagement", 0),
        now
    ))
    conn.commit()
    conn.close()


def classify_post(message):
    """Simple post type classification."""
    if not message:
        return "TEXT"
    msg_lower = message.lower()
    if "video" in msg_lower or "watch" in msg_lower:
        return "VIDEO"
    elif "photo" in msg_lower or "pic" in msg_lower:
        return "IMAGE"
    return "TEXT"


def fetch_page(page_label):
    """Fetch all data for a single page."""
    if page_label not in PAGE_TOKENS:
        print(f"Page '{page_label}' not found. Available: {list(PAGE_TOKENS.keys())}")
        return

    data = PAGE_TOKENS[page_label]
    if "error" in data:
        print(f"Error for {page_label}: {data['error']}")
        return

    page_id = data.get("page_id")
    page_name = data.get("page_name", page_label)
    token = data.get("page_access_token")

    print(f"\n{'='*60}")
    print(f"Fetching: {page_name}")
    print(f"Page ID: {page_id}")
    print(f"Fans: {data.get('fan_count', 'N/A'):,}")
    print(f"Starting from: {START_DATE}")
    print(f"{'='*60}")

    # Save page info
    save_page(data)

    # Fetch posts
    start_timestamp = int(datetime.strptime(START_DATE, "%Y-%m-%d").timestamp())

    url = f"https://graph.facebook.com/v21.0/{page_id}/posts"
    params = {
        "access_token": token,
        "fields": "id,message,created_time,permalink_url,shares",
        "limit": 100,
        "since": start_timestamp
    }

    all_posts = []
    page_num = 1

    print("\nFetching posts...")
    while True:
        try:
            resp = requests.get(url, params=params, timeout=30)
            result = resp.json()

            if "error" in result:
                print(f"API Error: {result['error'].get('message', 'Unknown')}")
                break

            posts = result.get("data", [])
            if not posts:
                break

            print(f"  Page {page_num}: {len(posts)} posts")
            all_posts.extend(posts)

            # Next page
            paging = result.get("paging", {})
            next_url = paging.get("next")

            if next_url:
                url = next_url
                params = {}
                page_num += 1
                time.sleep(0.5)
            else:
                break

        except Exception as e:
            print(f"Error: {e}")
            break

    print(f"\nTotal posts fetched: {len(all_posts)}")

    # Process and save each post
    print("\nProcessing posts...")
    saved = 0
    for i, post in enumerate(all_posts):
        post_id = post["id"]
        shares = post.get("shares", {}).get("count", 0)
        message = post.get("message", "")

        # Get reactions and comments count
        try:
            detail_url = f"https://graph.facebook.com/v21.0/{post_id}"
            detail_resp = requests.get(detail_url, params={
                "access_token": token,
                "fields": "reactions.summary(total_count),comments.summary(total_count)"
            }, timeout=10)
            detail = detail_resp.json()
            reactions = detail.get("reactions", {}).get("summary", {}).get("total_count", 0)
            comments = detail.get("comments", {}).get("summary", {}).get("total_count", 0)
        except:
            reactions = 0
            comments = 0

        # Calculate PES
        pes = (reactions * 1.0) + (comments * 2.0) + (shares * 3.0)
        engagement = reactions + comments + shares

        post_data = {
            "post_id": post_id,
            "message": message,
            "created_time": post.get("created_time"),
            "permalink": post.get("permalink_url"),
            "post_type": classify_post(message),
            "reactions": reactions,
            "comments": comments,
            "shares": shares,
            "pes": pes,
            "engagement": engagement
        }

        save_post(page_id, post_data)
        saved += 1

        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(all_posts)} posts...")

        time.sleep(0.2)  # Rate limiting

    print(f"\nSaved {saved} posts to database")
    return saved


def fetch_all_pages():
    """Fetch all pages one by one."""
    total = 0
    for label in PAGE_TOKENS.keys():
        if "error" not in PAGE_TOKENS[label]:
            count = fetch_page(label)
            if count:
                total += count
            time.sleep(1)

    print(f"\n{'='*60}")
    print(f"TOTAL: {total} posts from {len(PAGE_TOKENS)} pages")
    print(f"{'='*60}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Fetch specific page
        page_label = sys.argv[1]
        fetch_page(page_label)
    else:
        # Show available pages
        print("Available pages:")
        for label, data in PAGE_TOKENS.items():
            status = "OK" if "page_id" in data else f"Error: {data.get('error', 'Unknown')}"
            print(f"  - {label}: {status}")
        print("\nUsage: python fetch_single_page.py <page_label>")
        print("       python fetch_single_page.py Ashley")
        print("       Or run without args to see this help")
