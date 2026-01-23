#!/usr/bin/env python3
"""
Cleanup duplicate posts and pages in the database.

Handles:
1. Duplicate pages (same name, different IDs) - merges posts to primary page
2. Same page + same core post_id (different ID formats like pageid_postid vs postid)
3. Same content (title + page + publish_time) - catches Excel scientific notation imports
4. Scientific notation post IDs (1.22135E+17 format from CSV imports)

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


def merge_duplicate_pages(conn):
    """Merge pages with same name but different IDs."""
    cursor = conn.cursor()

    # Get all pages grouped by name
    cursor.execute('SELECT page_id, page_name, fan_count FROM pages ORDER BY page_name')
    pages_by_name = defaultdict(list)
    for row in cursor.fetchall():
        pages_by_name[row[1]].append({'id': row[0], 'name': row[1], 'fans': row[2] or 0})

    merged_pages = 0
    moved_posts = 0
    deleted_dups = 0

    for name, pages in pages_by_name.items():
        if len(pages) > 1:
            # Keep the one with most fans as primary
            pages_sorted = sorted(pages, key=lambda x: x['fans'], reverse=True)
            primary = pages_sorted[0]
            secondary_ids = [p['id'] for p in pages_sorted[1:]]

            # Get existing post signatures in primary
            cursor.execute('''
                SELECT LOWER(SUBSTR(title, 1, 100)), publish_time
                FROM posts WHERE page_id = ? AND title IS NOT NULL
            ''', (primary['id'],))
            existing = set((row[0], row[1]) for row in cursor.fetchall())

            # Move/merge posts from secondary pages
            for sec_id in secondary_ids:
                cursor.execute('SELECT post_id, title, publish_time FROM posts WHERE page_id = ?', (sec_id,))

                for post_id, title, pub_time in cursor.fetchall():
                    key = ((title or '').lower()[:100], pub_time)
                    if key not in existing:
                        cursor.execute('UPDATE posts SET page_id = ? WHERE post_id = ?', (primary['id'], post_id))
                        existing.add(key)
                        moved_posts += 1
                    else:
                        cursor.execute('DELETE FROM posts WHERE post_id = ?', (post_id,))
                        cursor.execute('DELETE FROM post_metrics WHERE post_id = ?', (post_id,))
                        deleted_dups += 1

                cursor.execute('DELETE FROM pages WHERE page_id = ?', (sec_id,))
                merged_pages += 1

    conn.commit()

    if merged_pages > 0:
        print(f"[CLEANUP] Merged {merged_pages} duplicate pages (moved {moved_posts} posts, removed {deleted_dups} duplicates)")

    return merged_pages


def cleanup_duplicates():
    if not DATABASE_PATH.exists():
        print("[CLEANUP] Database not found")
        return 0

    conn = sqlite3.connect(str(DATABASE_PATH), timeout=10)
    cursor = conn.cursor()

    # First, merge duplicate pages (same name, different IDs)
    merge_duplicate_pages(conn)

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
