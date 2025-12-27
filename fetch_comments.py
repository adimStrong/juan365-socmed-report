#!/usr/bin/env python3
"""
Fetch comment data from Facebook Graph API to analyze self-comments vs organic comments.

This script:
1. Gets all posts from the database
2. Fetches comments for each post from Facebook API
3. Counts self-comments (from page) vs organic comments (from users)
4. Updates the database with the breakdown

Usage:
    python fetch_comments.py
    python fetch_comments.py --limit 50  # Test with 50 posts first
"""

import sqlite3
import requests
import time
import argparse
from datetime import datetime

DATABASE_PATH = "data/juan365_socmed.db"

# Load page tokens from page_tokens.json
import json
with open("page_tokens.json", "r") as f:
    _tokens_data = json.load(f)

# Build PAGE_TOKENS: api_page_id -> token
PAGE_TOKENS = {}
PAGE_NAME_TO_API_ID = {}
for name, data in _tokens_data.items():
    if "page_id" in data and "page_access_token" in data:
        PAGE_TOKENS[data["page_id"]] = data["page_access_token"]
        PAGE_NAME_TO_API_ID[data["page_name"].lower()] = data["page_id"]

# Map database page_id (from CSV) to API page_id
# This will be built dynamically by matching page names
PAGE_ID_MAP = {}

def build_page_id_map():
    """Build mapping from CSV page IDs to Graph API page IDs based on page names."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT page_id, page_name FROM pages")

    csv_pages = [(row[0], row[1]) for row in cursor.fetchall() if row[1]]
    conn.close()

    # First pass: exact matches
    for csv_page_id, page_name in csv_pages:
        name_lower = page_name.lower().strip()
        for api_name, api_id in PAGE_NAME_TO_API_ID.items():
            if name_lower == api_name.lower().strip():
                PAGE_ID_MAP[csv_page_id] = api_id
                break

    # Second pass: fuzzy matches for unmatched pages
    for csv_page_id, page_name in csv_pages:
        if csv_page_id in PAGE_ID_MAP:
            continue
        name_lower = page_name.lower().strip()
        # Try matching with normalized names (remove spaces)
        name_normalized = name_lower.replace(" ", "")
        for api_name, api_id in PAGE_NAME_TO_API_ID.items():
            api_normalized = api_name.lower().replace(" ", "")
            if name_normalized == api_normalized:
                PAGE_ID_MAP[csv_page_id] = api_id
                break

    return PAGE_ID_MAP


def get_token_for_page(db_page_id):
    """Get the API token for a page based on database page_id."""
    api_page_id = PAGE_ID_MAP.get(db_page_id)
    if api_page_id:
        return PAGE_TOKENS.get(api_page_id), api_page_id
    return None, None


def fetch_comments_for_post(post_id, token, api_page_id):
    """
    Fetch comments for a post and count self-comments vs organic.

    Returns: (self_comments, organic_comments, has_page_comment)
    """
    # Facebook API expects post_id in format: {page_id}_{post_id}
    full_post_id = f"{api_page_id}_{post_id}"
    url = f"https://graph.facebook.com/v21.0/{full_post_id}/comments"
    params = {
        "fields": "from",
        "limit": 100,
        "access_token": token
    }

    self_comments = 0
    organic_comments = 0

    try:
        while url:
            response = requests.get(url, params=params)
            data = response.json()

            if "error" in data:
                # Post might be deleted or inaccessible
                return 0, 0, False

            comments = data.get("data", [])
            for comment in comments:
                commenter = comment.get("from", {})
                commenter_id = commenter.get("id", "")

                # Check if commenter is the page owner
                if commenter_id == api_page_id:
                    self_comments += 1
                else:
                    organic_comments += 1

            # Pagination
            paging = data.get("paging", {})
            url = paging.get("next")
            params = {}  # Next URL includes params

    except Exception as e:
        print(f"  Error: {e}")
        return 0, 0, False

    has_page_comment = self_comments > 0
    return self_comments, organic_comments, has_page_comment


def main():
    parser = argparse.ArgumentParser(description="Fetch comment data from Facebook API")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of posts to process (0 = all)")
    parser.add_argument("--skip-zero", action="store_true", help="Skip posts with 0 comments")
    args = parser.parse_args()

    print("=" * 60)
    print("Fetching Comment Data from Facebook API")
    print("=" * 60)

    # Build page ID mapping from CSV IDs to Graph API IDs
    print("\nBuilding page ID mapping...")
    build_page_id_map()
    print(f"Mapped {len(PAGE_ID_MAP)} pages:")
    for csv_id, api_id in PAGE_ID_MAP.items():
        print(f"  {csv_id} -> {api_id}")

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Get posts with comments
    query = """
        SELECT post_id, page_id, comments_count
        FROM posts
        WHERE comments_count > 0
        ORDER BY comments_count DESC
    """
    if args.limit > 0:
        query += f" LIMIT {args.limit}"

    cursor.execute(query)
    posts = cursor.fetchall()

    print(f"Found {len(posts)} posts with comments to process")
    print()

    processed = 0
    updated = 0
    errors = 0

    total_self = 0
    total_organic = 0

    for i, (post_id, db_page_id, comments_count) in enumerate(posts):
        token, api_page_id = get_token_for_page(db_page_id)

        if not token:
            print(f"[{i+1}/{len(posts)}] No token for page {db_page_id}, skipping")
            errors += 1
            continue

        print(f"[{i+1}/{len(posts)}] Post {post_id[:30]}... ({comments_count} comments)")

        self_comments, organic_comments, has_page_comment = fetch_comments_for_post(
            post_id, token, api_page_id
        )

        if self_comments + organic_comments > 0:
            print(f"  -> Self: {self_comments}, Organic: {organic_comments}")

            cursor.execute("""
                UPDATE posts
                SET page_comments = ?, has_page_comment = ?
                WHERE post_id = ?
            """, (self_comments, 1 if has_page_comment else 0, post_id))

            total_self += self_comments
            total_organic += organic_comments
            updated += 1
        else:
            print(f"  -> No comments found (post may be deleted)")

        processed += 1

        # Rate limiting - Facebook allows ~200 calls per hour
        time.sleep(0.5)

        # Commit every 50 posts
        if processed % 50 == 0:
            conn.commit()
            print(f"\n--- Checkpoint: {processed} posts processed ---\n")

    conn.commit()

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Posts processed: {processed}")
    print(f"Posts updated: {updated}")
    print(f"Errors: {errors}")
    print()
    print(f"Total self-comments: {total_self:,}")
    print(f"Total organic comments: {total_organic:,}")
    if total_self + total_organic > 0:
        pct = (total_self / (total_self + total_organic)) * 100
        print(f"Self-comment rate: {pct:.1f}%")

    # Show posts with most self-comments
    print()
    print("Posts with most self-comments:")
    cursor.execute("""
        SELECT p.post_id, pg.page_name, p.page_comments, p.comments_count
        FROM posts p
        LEFT JOIN pages pg ON p.page_id = pg.page_id
        WHERE p.page_comments > 0
        ORDER BY p.page_comments DESC
        LIMIT 10
    """)
    for row in cursor.fetchall():
        page = row[1].replace("Juana Babe ", "") if row[1] else "Unknown"
        print(f"  {page}: {row[2]} self / {row[3]} total")

    conn.close()
    print()
    print("Done! Run 'python export_static_data.py' to update Vercel data.")


if __name__ == "__main__":
    main()
