#!/usr/bin/env python3
"""
Cleanup duplicate posts in the database.
Duplicates = same page + same core post_id (with different ID formats like pageid_postid vs postid)
Keeps the version with highest engagement.

Run before export to ensure clean data.
"""

import sqlite3
from pathlib import Path
from collections import defaultdict

DATABASE_PATH = Path(__file__).parent / "data" / "juan365_socmed.db"


def get_core_id(post_id):
    """Extract core post ID (last part after underscore)."""
    post_id_str = str(post_id)
    if '_' in post_id_str:
        return post_id_str.split('_')[-1]
    return post_id_str


def cleanup_duplicates():
    if not DATABASE_PATH.exists():
        print("[CLEANUP] Database not found")
        return 0

    conn = sqlite3.connect(str(DATABASE_PATH))
    cursor = conn.cursor()

    # Get count before
    cursor.execute("SELECT COUNT(*) FROM posts")
    before_count = cursor.fetchone()[0]

    # Get all posts with engagement
    cursor.execute('''
        SELECT post_id, page_id, COALESCE(total_engagement, 0) as eng
        FROM posts
    ''')
    posts = cursor.fetchall()

    # Group by page_id + core_id
    groups = defaultdict(list)
    for post_id, page_id, eng in posts:
        core_id = get_core_id(post_id)
        key = (page_id, core_id)
        groups[key].append((post_id, eng))

    # Find and delete duplicates (keep highest engagement)
    deleted = 0
    for key, items in groups.items():
        if len(items) > 1:
            # Sort by engagement descending - keep highest
            items_sorted = sorted(items, key=lambda x: x[1], reverse=True)
            for item in items_sorted[1:]:
                cursor.execute('DELETE FROM posts WHERE post_id = ?', (item[0],))
                cursor.execute('DELETE FROM post_metrics WHERE post_id = ?', (item[0],))
                deleted += 1

    conn.commit()

    # Get count after
    cursor.execute("SELECT COUNT(*) FROM posts")
    after_count = cursor.fetchone()[0]

    conn.close()

    if deleted > 0:
        print(f"[CLEANUP] Removed {deleted} duplicate posts ({before_count} -> {after_count})")
    else:
        print(f"[CLEANUP] No duplicates found ({after_count} posts)")

    return deleted


if __name__ == "__main__":
    cleanup_duplicates()
