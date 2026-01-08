#!/usr/bin/env python3
"""
Juan365 - Send Daily Telegram Report
Run this at 8:00 AM via Windows Task Scheduler or cron.

Usage:
    python send_daily_report.py
    python send_daily_report.py --date 2026-01-07
"""

import os
import sys
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configuration
DATABASE_PATH = "data/juan365_socmed.db"

# Try to load from .env or use defaults
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("WARNING: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in environment")
    print("Please create a .env file with these values")


def get_daily_stats(date: str) -> dict:
    """Get statistics for a specific date."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as post_count,
            COALESCE(SUM(reactions_total), 0) as total_reactions,
            COALESCE(SUM(comments_count), 0) as total_comments,
            COALESCE(SUM(shares_count), 0) as total_shares,
            COALESCE(SUM(total_engagement), 0) as total_engagement
        FROM posts
        WHERE DATE(publish_time) = ?
    """, (date,))

    row = cursor.fetchone()
    conn.close()

    return {
        "date": date,
        "post_count": row[0] or 0,
        "total_reactions": row[1] or 0,
        "total_comments": row[2] or 0,
        "total_shares": row[3] or 0,
        "total_engagement": row[4] or 0,
    }


def get_latest_post() -> dict:
    """Get the most recent post."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.post_id,
            p.title,
            p.post_type,
            p.total_engagement,
            p.publish_time,
            pg.page_name
        FROM posts p
        LEFT JOIN pages pg ON p.page_id = pg.page_id
        ORDER BY p.publish_time DESC
        LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    if not row:
        return {}

    return {
        "post_id": row[0],
        "title": row[1] or "",
        "post_type": row[2] or "POST",
        "total_engagement": row[3] or 0,
        "publish_time": row[4],
        "page_name": row[5] or "Unknown",
    }


def get_top_posts(date: str, limit: int = 3) -> list:
    """Get top performing posts for a date."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.title,
            p.post_type,
            p.total_engagement,
            pg.page_name
        FROM posts p
        LEFT JOIN pages pg ON p.page_id = pg.page_id
        WHERE DATE(p.publish_time) = ?
        ORDER BY p.total_engagement DESC
        LIMIT ?
    """, (date, limit))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "title": row[0] or "",
            "post_type": row[1] or "POST",
            "total_engagement": row[2] or 0,
            "page_name": row[3] or "Unknown",
        }
        for row in rows
    ]


def generate_ai_insight(stats: dict, top_posts: list) -> str:
    """Generate AI insight using Ollama if available."""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "fb-analytics-core" / "src"))
        from fb_analytics_core.ai import InsightsGenerator

        generator = InsightsGenerator()
        return generator.generate_daily_insight_sync(stats, top_posts)
    except Exception:
        # Fallback insight
        if stats["post_count"] == 0:
            return "No posts yesterday. Consider maintaining a consistent posting schedule."

        avg = stats["total_engagement"] / stats["post_count"] if stats["post_count"] > 0 else 0

        if top_posts:
            top_type = top_posts[0].get("post_type", "content")
            return f"{top_type} content performing well with {avg:.0f} avg engagement per post."

        return f"Yesterday's {stats['post_count']} posts generated {stats['total_engagement']:,} total engagement."


def format_telegram_message(stats: dict, latest_post: dict, top_posts: list, ai_insight: str = None) -> str:
    """Format the daily report as a Telegram message."""
    message = f"<b>DAILY REPORT - {stats['date']}</b>\n\n"

    # Latest post section
    if latest_post:
        message += "<b>LATEST POST</b>\n"
        message += f"{latest_post.get('page_name', 'Unknown')} [{latest_post.get('post_type', 'POST')}]\n"
        title = (latest_post.get('title', '') or "No title")[:50]
        message += f"{title}...\n"
        message += f"Engagement: {latest_post.get('total_engagement', 0):,}\n\n"

    # Summary section
    message += "<b>SUMMARY</b>\n"
    message += f"Posts: {stats['post_count']}\n"
    message += f"Engagement: {stats['total_engagement']:,}\n"
    message += f"Reactions: {stats['total_reactions']:,}\n"
    message += f"Comments: {stats['total_comments']:,}\n"
    message += f"Shares: {stats['total_shares']:,}\n\n"

    # Top posts
    if top_posts:
        message += "<b>TOP POSTS</b>\n"
        for i, post in enumerate(top_posts[:3], 1):
            title = (post.get('title', '') or "No title")[:30]
            message += f"{i}. [{post['post_type']}] {title}... ({post['total_engagement']:,})\n"
        message += "\n"

    # AI Insight
    if ai_insight:
        message += "<b>AI INSIGHT</b>\n"
        message += f"{ai_insight}\n"

    return message


def send_telegram_message(message: str) -> dict:
    """Send message to Telegram."""
    import requests

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    response = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }, timeout=30)

    return response.json()


def main():
    parser = argparse.ArgumentParser(description="Send daily Telegram report")
    parser.add_argument("--date", help="Date to report (YYYY-MM-DD), default: yesterday")
    args = parser.parse_args()

    # Default to yesterday
    if args.date:
        report_date = args.date
    else:
        report_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"[{datetime.now()}] Generating report for {report_date}...")

    # Gather data
    stats = get_daily_stats(report_date)
    latest_post = get_latest_post()
    top_posts = get_top_posts(report_date)

    # Generate AI insight
    print("Generating AI insight...")
    ai_insight = generate_ai_insight(stats, top_posts)

    # Format message
    message = format_telegram_message(stats, latest_post, top_posts, ai_insight)

    # Send to Telegram
    print("Sending to Telegram...")
    result = send_telegram_message(message)

    if result.get("ok"):
        print(f"[{datetime.now()}] Report sent successfully!")
    else:
        print(f"[{datetime.now()}] Failed to send: {result}")

    return result


if __name__ == "__main__":
    main()
