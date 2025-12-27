#!/usr/bin/env python3
"""Export JuanBabes analytics data to CSV files."""

import sqlite3
import csv
import os
from datetime import datetime

DATABASE_PATH = "data/juanbabes_analytics.db"
OUTPUT_DIR = "reports"

def export_pages():
    """Export page comparison data."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            pg.page_id,
            pg.page_name,
            pg.fan_count,
            pg.followers_count,
            COUNT(p.post_id) as post_count,
            COALESCE(SUM(p.reactions_total), 0) as total_reactions,
            COALESCE(SUM(p.comments_count), 0) as total_comments,
            COALESCE(SUM(p.shares_count), 0) as total_shares,
            COALESCE(SUM(p.total_engagement), 0) as total_engagement,
            COALESCE(AVG(p.pes), 0) as avg_pes
        FROM pages pg
        LEFT JOIN posts p ON pg.page_id = p.page_id
            AND (p.reactions_total > 0 OR p.comments_count > 0 OR p.shares_count > 0)
        GROUP BY pg.page_id, pg.page_name, pg.fan_count, pg.followers_count
        HAVING COUNT(p.post_id) > 0
        ORDER BY total_engagement DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    filepath = os.path.join(OUTPUT_DIR, "page_comparison.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Page ID", "Page Name", "Fan Count", "Followers",
            "Posts", "Reactions", "Comments", "Shares",
            "Total Engagement", "Avg PES", "Avg Engagement"
        ])
        for row in rows:
            avg_eng = round(row[8] / row[4], 1) if row[4] > 0 else 0
            writer.writerow([
                row[0], row[1], row[2] or "", row[3] or "",
                row[4], row[5], row[6], row[7],
                row[8], round(row[9], 1), avg_eng
            ])

    print(f"Exported {len(rows)} pages to {filepath}")
    return len(rows)


def export_posts():
    """Export all posts data."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.post_id,
            pg.page_name,
            p.title,
            p.post_type,
            p.publish_time,
            p.permalink,
            COALESCE(p.reactions_total, 0) as reactions,
            COALESCE(p.comments_count, 0) as comments,
            COALESCE(p.shares_count, 0) as shares,
            COALESCE(p.total_engagement, 0) as engagement,
            COALESCE(p.pes, 0) as pes
        FROM posts p
        LEFT JOIN pages pg ON p.page_id = pg.page_id
        WHERE p.reactions_total > 0 OR p.comments_count > 0 OR p.shares_count > 0
        ORDER BY p.total_engagement DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    filepath = os.path.join(OUTPUT_DIR, "all_posts.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Post ID", "Page", "Title", "Type", "Publish Time",
            "Permalink", "Reactions", "Comments", "Shares",
            "Engagement", "PES Score"
        ])
        for row in rows:
            writer.writerow(row)

    print(f"Exported {len(rows)} posts to {filepath}")
    return len(rows)


def export_daily_stats():
    """Export daily engagement stats."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            DATE(publish_time) as post_date,
            COUNT(*) as post_count,
            COALESCE(SUM(reactions_total), 0) as reactions,
            COALESCE(SUM(comments_count), 0) as comments,
            COALESCE(SUM(shares_count), 0) as shares,
            COALESCE(SUM(total_engagement), 0) as engagement,
            COALESCE(SUM(pes), 0) as pes
        FROM posts
        WHERE publish_time IS NOT NULL
            AND (reactions_total > 0 OR comments_count > 0 OR shares_count > 0)
        GROUP BY DATE(publish_time)
        ORDER BY post_date
    """)

    rows = cursor.fetchall()
    conn.close()

    filepath = os.path.join(OUTPUT_DIR, "daily_engagement.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Date", "Posts", "Reactions", "Comments", "Shares",
            "Engagement", "PES Score"
        ])
        for row in rows:
            writer.writerow([
                row[0], row[1], row[2], row[3], row[4],
                row[5], round(row[6], 1)
            ])

    print(f"Exported {len(rows)} days to {filepath}")
    return len(rows)


def export_top_posts():
    """Export top 50 posts."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.post_id,
            pg.page_name,
            p.title,
            p.post_type,
            p.publish_time,
            p.permalink,
            COALESCE(p.reactions_total, 0) as reactions,
            COALESCE(p.comments_count, 0) as comments,
            COALESCE(p.shares_count, 0) as shares,
            COALESCE(p.total_engagement, 0) as engagement,
            COALESCE(p.pes, 0) as pes
        FROM posts p
        LEFT JOIN pages pg ON p.page_id = pg.page_id
        WHERE p.reactions_total > 0 OR p.comments_count > 0 OR p.shares_count > 0
        ORDER BY p.total_engagement DESC
        LIMIT 50
    """)

    rows = cursor.fetchall()
    conn.close()

    filepath = os.path.join(OUTPUT_DIR, "top_50_posts.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Rank", "Post ID", "Page", "Title", "Type", "Publish Time",
            "Permalink", "Reactions", "Comments", "Shares",
            "Engagement", "PES Score"
        ])
        for i, row in enumerate(rows, 1):
            writer.writerow([i] + list(row))

    print(f"Exported top {len(rows)} posts to {filepath}")
    return len(rows)


def main():
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("JuanBabes Analytics - CSV Export")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    export_pages()
    export_posts()
    export_daily_stats()
    export_top_posts()

    print("\n" + "=" * 60)
    print(f"All reports saved to: {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
