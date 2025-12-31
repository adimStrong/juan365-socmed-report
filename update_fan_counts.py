#!/usr/bin/env python3
"""Update fan counts for all pages from Facebook API."""

import json
import sqlite3
import requests
from datetime import datetime

DATABASE_PATH = "data/juan365_socmed.db"

# Load page tokens
with open("page_tokens.json", "r") as f:
    PAGE_TOKENS = json.load(f)


def fetch_page_info(page_id, token):
    """Fetch page info including fan count from Facebook API."""
    url = f"https://graph.facebook.com/v21.0/{page_id}"
    params = {
        "access_token": token,
        "fields": "id,name,fan_count,followers_count"
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  Error: {response.status_code} - {response.text[:100]}")
            return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def update_fan_counts():
    """Update fan counts in database for all pages."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    print("=" * 60)
    print("Updating Fan Counts from Facebook API")
    print("=" * 60)

    updated = 0

    for page_name, page_data in PAGE_TOKENS.items():
        page_id = page_data.get("page_id")
        token = page_data.get("page_access_token")

        if not page_id or not token:
            print(f"\n[SKIP] {page_name}: Missing page_id or token")
            continue

        print(f"\n[{page_name}]")
        print(f"  Page ID: {page_id}")

        info = fetch_page_info(page_id, token)

        if info:
            fan_count = info.get("fan_count")
            followers_count = info.get("followers_count")

            print(f"  Fans: {fan_count:,}" if fan_count else "  Fans: N/A")
            print(f"  Followers: {followers_count:,}" if followers_count else "  Followers: N/A")

            # Update database by page_name (case-insensitive, since DB uses old page_ids)
            db_page_name = page_data.get("page_name", page_name)
            cursor.execute("""
                UPDATE pages
                SET fan_count = ?, followers_count = ?, updated_at = ?
                WHERE LOWER(page_name) = LOWER(?)
            """, (fan_count, followers_count, datetime.now().isoformat(), db_page_name))

            if cursor.rowcount > 0:
                print(f"  [OK] Updated in database")
                updated += 1
            else:
                print(f"  [SKIP] Page not found in database: {db_page_name}")
        else:
            print(f"  [FAIL] Could not fetch page info")

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print(f"Updated {updated} pages")
    print("=" * 60)
    print("\nNow run: python export_static_data.py")


if __name__ == "__main__":
    update_fan_counts()
