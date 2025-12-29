#!/usr/bin/env python3
"""Import manually exported CSV files from Meta Business Suite."""

import csv
import sqlite3
import os
from datetime import datetime
from glob import glob

DATABASE_PATH = "data/juanbabes_analytics.db"
EXPORTS_FOLDER = "exports/from content manual Export"


def get_conn():
    return sqlite3.connect(DATABASE_PATH)


def parse_datetime(dt_str):
    """Parse datetime from CSV format."""
    if not dt_str:
        return None
    try:
        # Format: 10/01/2025 04:34
        return datetime.strptime(dt_str, "%m/%d/%Y %H:%M").isoformat()
    except:
        return dt_str


def safe_int(val):
    """Safely convert to int."""
    if not val or val == "":
        return 0
    try:
        return int(float(val))
    except:
        return 0


def import_csv(filepath):
    """Import a single CSV file."""
    print(f"\nImporting: {os.path.basename(filepath)}")

    conn = get_conn()
    cursor = conn.cursor()

    imported = 0
    pages_seen = set()

    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            page_id = row.get("Page ID", "")
            page_name = row.get("Page name", "")
            post_id = row.get("Post ID", "")

            if not post_id or not page_id:
                continue

            # Track pages
            if page_id not in pages_seen:
                pages_seen.add(page_id)
                # Save/update page info (use REPLACE to ensure page_name is updated)
                cursor.execute("""
                    INSERT OR REPLACE INTO pages (page_id, page_name, created_at, updated_at)
                    VALUES (?, ?, COALESCE((SELECT created_at FROM pages WHERE page_id = ?), ?), ?)
                """, (page_id, page_name, page_id, datetime.now().isoformat(), datetime.now().isoformat()))

            # Parse post data
            title = row.get("Title", "")[:200] if row.get("Title") else ""
            permalink = row.get("Permalink", "")
            post_type = row.get("Post type", "TEXT")
            publish_time = parse_datetime(row.get("Publish time", ""))

            reactions = safe_int(row.get("Reactions", 0))
            comments = safe_int(row.get("Comments", 0))
            shares = safe_int(row.get("Shares", 0))
            views = safe_int(row.get("Views", 0))
            reach = safe_int(row.get("Reach", 0))

            # Calculate engagement metrics
            total_engagement = reactions + comments + shares
            pes = (reactions * 1.0) + (comments * 2.0) + (shares * 3.0)

            # Insert or update post
            cursor.execute("""
                INSERT OR REPLACE INTO posts
                (post_id, page_id, title, permalink, post_type, publish_time,
                 reactions_total, comments_count, shares_count, views_count, reach_count,
                 pes, total_engagement, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post_id,
                page_id,
                title,
                permalink,
                post_type,
                publish_time,
                reactions,
                comments,
                shares,
                views,
                reach,
                pes,
                total_engagement,
                datetime.now().isoformat()
            ))

            imported += 1

    conn.commit()
    conn.close()

    print(f"  Imported {imported} posts from {len(pages_seen)} pages")
    return imported, pages_seen


def main():
    print("=" * 60)
    print("Importing Manual CSV Exports")
    print("=" * 60)

    # Find all CSV files
    csv_files = glob(os.path.join(EXPORTS_FOLDER, "*.csv"))

    if not csv_files:
        print(f"No CSV files found in {EXPORTS_FOLDER}")
        return

    print(f"Found {len(csv_files)} CSV files")

    total_posts = 0
    all_pages = set()

    for csv_file in sorted(csv_files):
        count, pages = import_csv(csv_file)
        total_posts += count
        all_pages.update(pages)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total posts imported: {total_posts}")
    print(f"Total pages: {len(all_pages)}")

    # Show page summary
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.page_name, COUNT(po.post_id) as post_count,
               SUM(po.reactions_total) as total_reactions,
               SUM(po.comments_count) as total_comments,
               SUM(po.shares_count) as total_shares,
               SUM(po.views_count) as total_views,
               SUM(po.reach_count) as total_reach
        FROM pages p
        LEFT JOIN posts po ON p.page_id = po.page_id
        GROUP BY p.page_id
        ORDER BY post_count DESC
    """)

    print("\nPage breakdown:")
    for row in cursor.fetchall():
        name, posts, reactions, comments, shares, views, reach = row
        print(f"  {name}: {posts} posts, {reactions or 0} reactions, {views or 0} views, {reach or 0} reach")

    conn.close()


if __name__ == "__main__":
    main()
