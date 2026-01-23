#!/usr/bin/env python3
"""
Cleanup duplicate posts in the database.

Handles 3 types of duplicates:
1. Same page + same core post_id (different ID formats like pageid_postid vs postid)
2. Same content (title + page + publish_time) - catches Excel scientific notation imports
3. Scientific notation post IDs (1.22135E+17 format from CSV imports)

Keeps the version with proper post_id format and highest engagement.
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

    conn = sqlite3.connect(str(DATABASE_PATH), timeout=10)
    cursor = conn.cursor()

    # Get count before
    cursor.execute("SELECT COUNT(*) FROM posts")
    before_count = cursor.fetchone()[0]

    deleted = 0

    # === Method 1: Core ID duplicates ===
    cursor.execute('''
        SELECT post_id, page_id, COALESCE(total_engagement, 0) as eng
        FROM posts
    ''')
    posts = cursor.fetchall()

    groups = defaultdict(list)
    for post_id, page_id, eng in posts:
        core_id = get_core_id(post_id)
        key = (page_id, core_id)
        groups[key].append((post_id, eng))

    for key, items in groups.items():
        if len(items) > 1:
            items_sorted = sorted(items, key=lambda x: x[1], reverse=True)
            for item in items_sorted[1:]:
                cursor.execute('DELETE FROM posts WHERE post_id = ?', (item[0],))
                cursor.execute('DELETE FROM post_metrics WHERE post_id = ?', (item[0],))
                deleted += 1

    # === Method 2: Content-based duplicates (same title + page + time) ===
    cursor.execute('''
        SELECT post_id, page_id, title, publish_time, COALESCE(total_engagement, 0) as eng
        FROM posts
        WHERE title IS NOT NULL AND title != ''
    ''')

    content_groups = defaultdict(list)
    for post_id, page_id, title, pub_time, eng in cursor.fetchall():
        # Normalize title for comparison
        norm_title = (title or '').strip().lower()[:100]
        key = (page_id, norm_title, pub_time)
        content_groups[key].append((post_id, eng))

    for key, items in content_groups.items():
        if len(items) > 1:
            # Prefer non-scientific notation IDs, then highest engagement
            items_sorted = sorted(items, key=lambda x: ('E+' in str(x[0]), -x[1]))
            for post_id, _ in items_sorted[1:]:
                cursor.execute('DELETE FROM posts WHERE post_id = ?', (post_id,))
                cursor.execute('DELETE FROM post_metrics WHERE post_id = ?', (post_id,))
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
