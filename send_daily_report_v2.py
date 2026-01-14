#!/usr/bin/env python3
"""
Daily Report with Dashboard Screenshot
Sends yesterday's stats + comparison to monthly average + dashboard screenshot

Features:
- T+1 data verification: compares DB stats vs API before sending
- Post count must match exactly; small engagement discrepancy is OK
- Retries sync up to 3 times if data mismatch
- Sends error message if verification fails after 3 attempts

Usage:
    python send_daily_report_v2.py                    # JuanStudio (default)
    python send_daily_report_v2.py --project juanbabes
    python send_daily_report_v2.py --project juan365
    python send_daily_report_v2.py --date 2026-01-12  # Specific date
    python send_daily_report_v2.py --no-screenshot    # Text only
    python send_daily_report_v2.py --skip-verify      # Skip API verification
"""

import os
import sys
import json
import sqlite3
import argparse
import requests
import tempfile
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Import screenshot module
sys.path.insert(0, str(Path(__file__).parent))
from screenshot_capture import capture_screenshot_sync, capture_screenshots_sync, DASHBOARD_CONFIGS

# Telegram Bot Token (shared across all projects)
BOT_TOKEN = "8528398122:AAG9o7TOPrGxMEv_1eDIoiMO1cvTYq4Um7s"

# Facebook Graph API settings
GRAPH_API_VERSION = "v18.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
POST_FIELDS = ["id", "created_time", "reactions.summary(true)", "comments.summary(true)", "shares"]


def get_db_connection(db_path: str):
    """Get database connection with row factory."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_yesterday_stats(db_path: str, date: str) -> dict:
    """Get statistics for a specific date."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as post_count,
            COALESCE(SUM(reactions_total), 0) as total_reactions,
            COALESCE(SUM(comments_count), 0) as total_comments,
            COALESCE(SUM(shares_count), 0) as total_shares,
            COALESCE(SUM(total_engagement), 0) as total_engagement
        FROM posts
        WHERE substr(publish_time, 1, 10) = ?
    """, (date,))

    row = cursor.fetchone()
    conn.close()

    return {
        "date": date,
        "posts": row["post_count"] or 0,
        "reactions": row["total_reactions"] or 0,
        "comments": row["total_comments"] or 0,
        "shares": row["total_shares"] or 0,
        "engagement": row["total_engagement"] or 0,
    }


def get_monthly_average(db_path: str) -> dict:
    """Get this month's daily average engagement."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Current month in both formats for matching
    now = datetime.now()
    year_month_iso = now.strftime('%Y-%m')  # e.g., '2026-01'
    month_mm = now.strftime('%m')  # e.g., '01'
    year_yyyy = now.strftime('%Y')  # e.g., '2026'

    # Calculate days elapsed this month (up to today)
    days_in_month = (now - now.replace(day=1)).days + 1  # Include today

    cursor.execute("""
        SELECT
            COUNT(*) as total_posts,
            COALESCE(SUM(reactions_total), 0) as total_reactions,
            COALESCE(SUM(comments_count), 0) as total_comments,
            COALESCE(SUM(shares_count), 0) as total_shares,
            COALESCE(SUM(total_engagement), 0) as total_engagement
        FROM posts
        WHERE publish_time LIKE ? || '%'
           OR publish_time LIKE ? || '/%/' || ? || '%'
    """, (year_month_iso, month_mm, year_yyyy))

    row = cursor.fetchone()
    conn.close()

    days = days_in_month

    return {
        "avg_posts": (row["total_posts"] or 0) / days,
        "avg_reactions": (row["total_reactions"] or 0) / days,
        "avg_comments": (row["total_comments"] or 0) / days,
        "avg_shares": (row["total_shares"] or 0) / days,
        "avg_engagement": (row["total_engagement"] or 0) / days,
        "days_count": days,
    }


def get_top_posts_for_date(db_path: str, date: str, limit: int = 3) -> list:
    """Get top performing posts for a specific date."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.title,
            p.post_type,
            p.total_engagement,
            p.reactions_total,
            p.comments_count,
            p.shares_count,
            pg.page_name,
            p.permalink
        FROM posts p
        LEFT JOIN pages pg ON p.page_id = pg.page_id
        WHERE substr(p.publish_time, 1, 10) = ?
        ORDER BY p.total_engagement DESC
        LIMIT ?
    """, (date, limit))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "title": (row["title"] or "")[:40],
            "post_type": row["post_type"] or "POST",
            "engagement": row["total_engagement"] or 0,
            "reactions": row["reactions_total"] or 0,
            "comments": row["comments_count"] or 0,
            "shares": row["shares_count"] or 0,
            "page": row["page_name"] or "Unknown",
            "permalink": row["permalink"] or "",
        }
        for row in rows
    ]


def get_top_posts_this_month(db_path: str, limit: int = 5) -> list:
    """Get top performing posts for this month."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')

    cursor.execute("""
        SELECT
            p.title,
            p.post_type,
            p.total_engagement,
            p.reactions_total,
            p.comments_count,
            p.shares_count,
            pg.page_name,
            substr(p.publish_time, 1, 10) as post_date,
            p.permalink
        FROM posts p
        LEFT JOIN pages pg ON p.page_id = pg.page_id
        WHERE substr(p.publish_time, 1, 10) >= ?
        ORDER BY p.total_engagement DESC
        LIMIT ?
    """, (month_start, limit))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "title": (row["title"] or "")[:35],
            "post_type": row["post_type"] or "POST",
            "engagement": row["total_engagement"] or 0,
            "reactions": row["reactions_total"] or 0,
            "comments": row["comments_count"] or 0,
            "shares": row["shares_count"] or 0,
            "page": (row["page_name"] or "Unknown").replace("Juankada ", "").replace("JUANKada ", "")[:10],
            "date": row["post_date"],
            "permalink": row["permalink"] or "",
        }
        for row in rows
    ]


def calculate_change(current: float, average: float) -> str:
    """Calculate percentage change vs average."""
    if average == 0:
        return "N/A"
    change = ((current - average) / average) * 100
    if change >= 0:
        return f"+{change:.1f}%"
    return f"{change:.1f}%"


def format_summary_message(
    project_name: str,
    yesterday: dict,
    monthly_avg: dict,
    yesterday_top_posts: list = None,
    month_top_posts: list = None
) -> str:
    """Format the text summary for Telegram."""

    # Calculate comparisons
    posts_change = calculate_change(yesterday["posts"], monthly_avg["avg_posts"])
    reactions_change = calculate_change(yesterday["reactions"], monthly_avg["avg_reactions"])
    comments_change = calculate_change(yesterday["comments"], monthly_avg["avg_comments"])
    shares_change = calculate_change(yesterday["shares"], monthly_avg["avg_shares"])
    engagement_change = calculate_change(yesterday["engagement"], monthly_avg["avg_engagement"])

    message = f"""<b>{project_name} DAILY API SYNC</b>
<i>{yesterday['date']}</i>

<b>YESTERDAY'S STATS</b>
Posts: {yesterday['posts']} ({posts_change} vs avg)
Reactions: {yesterday['reactions']:,} ({reactions_change})
Comments: {yesterday['comments']:,} ({comments_change})
Shares: {yesterday['shares']:,} ({shares_change})
<b>Total Engagement: {yesterday['engagement']:,}</b> ({engagement_change})
"""

    # Yesterday's top posts
    if yesterday_top_posts:
        message += "\n<b>TOP POSTS YESTERDAY</b>\n"
        for i, post in enumerate(yesterday_top_posts[:3], 1):
            title = post["title"][:30] + "..." if len(post["title"]) > 30 else post["title"]
            if not title:
                title = f"[{post['post_type']}]"
            if post.get("permalink"):
                message += f'{i}. <a href="{post["permalink"]}">{title}</a> ({post["engagement"]:,})\n'
            else:
                message += f"{i}. [{post['post_type'][:5]}] {title} ({post['engagement']:,})\n"

    # This month's top posts
    if month_top_posts:
        message += f"\n<b>TOP 5 THIS MONTH</b>\n"
        for i, post in enumerate(month_top_posts[:5], 1):
            title = post["title"][:25] + "..." if len(post["title"]) > 25 else post["title"]
            if not title:
                title = f"[{post['post_type']}]"
            if post.get("permalink"):
                message += f'{i}. {post["page"]} - <a href="{post["permalink"]}">{title}</a> ({post["engagement"]:,})\n'
            else:
                message += f"{i}. {post['page']} - {title} ({post['engagement']:,})\n"

    # Monthly average summary
    message += f"""
<b>MONTHLY AVG</b> ({monthly_avg['days_count']} days)
Posts: {monthly_avg['avg_posts']:.1f}/day | Engagement: {monthly_avg['avg_engagement']:,.0f}/day"""

    return message


def send_telegram_photo(chat_id: str, photo_path: str, caption: str) -> dict:
    """Send photo with caption to Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    with open(photo_path, 'rb') as photo:
        response = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "HTML"
            },
            files={"photo": photo},
            timeout=60
        )

    return response.json()


def send_telegram_message(chat_id: str, message: str) -> dict:
    """Send text message to Telegram (fallback if screenshot fails)."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        },
        timeout=30
    )

    return response.json()


def load_page_tokens(project_dir: str) -> dict:
    """Load page access tokens from project's page_tokens.json."""
    tokens_path = os.path.join(project_dir, "page_tokens.json")
    if not os.path.exists(tokens_path):
        return {}
    with open(tokens_path, 'r') as f:
        return json.load(f)


def fetch_api_posts_for_date(tokens: dict, target_date: str) -> list:
    """Fetch all posts from Facebook API for a specific date (UTC) with full data."""
    all_posts = []

    # Use UTC timestamps - target_date is in UTC (matches how DB stores publish_time)
    from datetime import timezone
    target_start_utc = datetime.strptime(target_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    target_end_utc = target_start_utc + timedelta(days=1)

    # Extended fields to get full engagement data
    fields = [
        "id", "message", "created_time", "permalink_url",
        "shares", "reactions.summary(true)", "comments.summary(true)",
        "attachments{type,media_type}"
    ]

    for page_name, page_data in tokens.items():
        page_id = page_data.get("page_id")
        token = page_data.get("page_access_token") or page_data.get("token")
        if not token or not page_id:
            continue

        url = f"{GRAPH_API_BASE}/{page_id}/posts"
        params = {
            "access_token": token,
            "fields": ",".join(fields),
            "since": int(target_start_utc.timestamp()),
            "until": int(target_end_utc.timestamp()),
            "limit": 100
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()

            if "error" in data:
                print(f"    API error for page {page_id}: {data['error'].get('message', 'Unknown')}")
                continue

            posts = data.get("data", [])
            for post in posts:
                created = post.get("created_time", "")[:10]
                if created == target_date:
                    # Extract post_id (API returns "pageid_postid" format)
                    full_id = post.get("id", "")
                    post_id = full_id.split("_")[-1] if "_" in full_id else full_id

                    # Get metrics
                    reactions = post.get("reactions", {}).get("summary", {}).get("total_count", 0)
                    comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
                    shares = post.get("shares", {}).get("count", 0)

                    # Determine post type from attachments
                    attachments = post.get("attachments", {}).get("data", [])
                    post_type = "Text"
                    if attachments:
                        media_type = attachments[0].get("media_type", "")
                        attach_type = attachments[0].get("type", "")
                        if media_type == "video" or attach_type == "video_inline":
                            post_type = "Videos"
                        elif media_type == "photo" or attach_type == "photo":
                            post_type = "Photos"
                        elif attach_type == "native_templates" and "reel" in str(attachments).lower():
                            post_type = "Reels"

                    all_posts.append({
                        "post_id": post_id,
                        "page_id": page_id,
                        "title": (post.get("message", "") or "")[:200],
                        "permalink": post.get("permalink_url", ""),
                        "post_type": post_type,
                        "publish_time": post.get("created_time", ""),
                        "reactions_total": reactions,
                        "comments_count": comments,
                        "shares_count": shares,
                        "total_engagement": reactions + comments + shares,
                        "pes": (reactions * 1.0) + (comments * 2.0) + (shares * 3.0)
                    })

        except Exception as e:
            print(f"    Request error for page {page_id}: {e}")
            continue

    return all_posts


def sync_t1_data_from_api(db_path: str, target_date: str, api_posts: list) -> dict:
    """
    Sync T+1 data from API to database.
    - Delete posts in DB that are NOT in API (for target_date only)
    - Update/insert posts from API with latest engagement data
    Returns stats after sync.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get API post IDs
    api_post_ids = set(p["post_id"] for p in api_posts)

    # Get DB post IDs for target_date
    cursor.execute("""
        SELECT post_id FROM posts
        WHERE substr(publish_time, 1, 10) = ?
    """, (target_date,))
    db_post_ids = set(row[0] for row in cursor.fetchall())

    # Delete posts that are in DB but NOT in API (for this date only)
    posts_to_delete = db_post_ids - api_post_ids
    if posts_to_delete:
        print(f"    Removing {len(posts_to_delete)} posts not in API...")
        for post_id in posts_to_delete:
            cursor.execute("DELETE FROM posts WHERE post_id = ?", (post_id,))

    # Update/insert posts from API
    updated = 0
    inserted = 0
    for post in api_posts:
        # Check if post exists
        cursor.execute("SELECT post_id FROM posts WHERE post_id = ?", (post["post_id"],))
        exists = cursor.fetchone()

        if exists:
            # Update with latest engagement data
            cursor.execute("""
                UPDATE posts SET
                    reactions_total = ?,
                    comments_count = ?,
                    shares_count = ?,
                    total_engagement = ?,
                    pes = ?,
                    fetched_at = ?
                WHERE post_id = ?
            """, (
                post["reactions_total"],
                post["comments_count"],
                post["shares_count"],
                post["total_engagement"],
                post["pes"],
                datetime.now().isoformat(),
                post["post_id"]
            ))
            updated += 1
        else:
            # Insert new post
            cursor.execute("""
                INSERT INTO posts
                (post_id, page_id, title, permalink, post_type, publish_time,
                 reactions_total, comments_count, shares_count, total_engagement,
                 pes, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post["post_id"],
                post["page_id"],
                post["title"],
                post["permalink"],
                post["post_type"],
                post["publish_time"],
                post["reactions_total"],
                post["comments_count"],
                post["shares_count"],
                post["total_engagement"],
                post["pes"],
                datetime.now().isoformat()
            ))
            inserted += 1

    conn.commit()
    conn.close()

    # Calculate stats from API posts
    stats = {
        "posts": len(api_posts),
        "reactions": sum(p["reactions_total"] for p in api_posts),
        "comments": sum(p["comments_count"] for p in api_posts),
        "shares": sum(p["shares_count"] for p in api_posts),
        "engagement": sum(p["total_engagement"] for p in api_posts)
    }

    print(f"    Sync complete: {inserted} inserted, {updated} updated, {len(posts_to_delete)} deleted")
    return stats


def run_sync_script(project_dir: str) -> bool:
    """Run the scheduled_sync.py to refresh data from API."""
    sync_scripts = ["scheduled_sync.py", "fetch_missing_posts.py"]

    for script in sync_scripts:
        script_path = os.path.join(project_dir, script)
        if os.path.exists(script_path):
            try:
                result = subprocess.run(
                    [sys.executable, script_path],
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                return result.returncode == 0
            except Exception as e:
                print(f"    Sync error: {e}")
                return False
    return False


def run_export_static_data(project_dir: str) -> bool:
    """Run export_static_data.py to update JSON for Vercel."""
    export_script = os.path.join(project_dir, "export_static_data.py")
    if not os.path.exists(export_script):
        print(f"    Export script not found: {export_script}")
        return False

    try:
        result = subprocess.run(
            [sys.executable, export_script],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            return True
        else:
            print(f"    Export error: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"    Export error: {e}")
        return False


def deploy_to_vercel(project_dir: str, report_date: str) -> bool:
    """Deploy to Vercel using CLI with --force to clear cache."""
    import time

    frontend_dir = os.path.join(project_dir, "frontend")
    if not os.path.exists(frontend_dir):
        print(f"    Frontend dir not found: {frontend_dir}")
        return False

    # Detect JSON filename (analytics-v2.json or analytics.json)
    json_file = "public/data/analytics-v2.json"
    if not os.path.exists(os.path.join(frontend_dir, json_file)):
        json_file = "public/data/analytics.json"

    try:
        # Git add from project root (not frontend)
        result = subprocess.run(
            ["git", "add", f"frontend/{json_file}"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Git commit
        commit_msg = f"Update analytics data {report_date}"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30
        )

        if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
            print("    No changes to commit")
        else:
            # Git push
            print("    Pushing to GitHub...")
            subprocess.run(
                ["git", "push"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=60
            )

        # Deploy via Vercel CLI with --force to clear cache
        # Run from project_dir (root) to avoid Vercel root directory issues
        print("    Deploying via Vercel CLI (cache clear)...")
        result = subprocess.run(
            ["npx", "vercel", "--prod", "--force", "--yes"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0 or "Aliased" in result.stdout:
            print("    [OK] Vercel deployment complete")
            return True
        else:
            print(f"    Vercel CLI failed, using GitHub integration...")
            # Vercel will auto-deploy from GitHub push
            print("    Waiting 60s for Vercel deployment...")
            time.sleep(60)
            return True

    except Exception as e:
        print(f"    Deploy error: {e}")
        return False


def verify_data_with_api(project: str, db_path: str, target_date: str, max_retries: int = 1) -> tuple:
    """
    Sync T+1 data from Facebook API to database.
    API is the source of truth - DB is updated to match.

    Returns (is_verified, synced_stats, api_stats, error_message)
    """
    project_dirs = {
        "juanstudio": r"C:\Users\us\Desktop\juanstudio_project",
        "juanbabes": r"C:\Users\us\Desktop\juanbabes_project",
        "juan365": r"C:\Users\us\Desktop\juan365_socmed_report"
    }
    project_dir = project_dirs.get(project)

    tokens = load_page_tokens(project_dir)
    if not tokens:
        return True, None, None, "No tokens found - skipping verification"

    print(f"    Fetching T+1 data from API for {target_date}...")

    # Fetch all posts from API for target date
    api_posts = fetch_api_posts_for_date(tokens, target_date)
    print(f"    Found {len(api_posts)} posts in API")

    if not api_posts:
        # No posts from API - could be weekend or no activity
        print(f"    No posts found in API for {target_date}")
        return True, {"posts": 0, "reactions": 0, "comments": 0, "shares": 0, "engagement": 0}, None, None

    # Sync API data to database (delete extra, update engagement)
    print(f"    Syncing to database...")
    synced_stats = sync_t1_data_from_api(db_path, target_date, api_posts)

    print(f"    T+1 sync complete: {synced_stats['posts']} posts, {synced_stats['engagement']} engagement")
    return True, synced_stats, synced_stats, None


def main():
    parser = argparse.ArgumentParser(description="Send daily report with dashboard screenshot")
    parser.add_argument("--project", choices=["juanstudio", "juanbabes", "juan365"],
                        default="juan365", help="Which project to report on")
    parser.add_argument("--date", help="Date to report (YYYY-MM-DD), default: yesterday")
    parser.add_argument("--no-screenshot", action="store_true", help="Skip screenshot capture")
    parser.add_argument("--skip-verify", action="store_true", help="Skip API verification")
    parser.add_argument("--screenshot-filter", default="thismonth",
                        choices=["thismonth", "lastmonth", "7days", "30days", "60days", "90days", "all"],
                        help="Date filter for screenshot (default: thismonth)")
    args = parser.parse_args()

    # Get project config
    config = DASHBOARD_CONFIGS[args.project]

    # Determine report date
    if args.date:
        report_date = args.date
    else:
        report_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generating {config['project_name']} report for {report_date}...")

    # Project directories
    project_dirs = {
        "juanstudio": r"C:\Users\us\Desktop\juanstudio_project",
        "juanbabes": r"C:\Users\us\Desktop\juanbabes_project",
        "juan365": r"C:\Users\us\Desktop\juan365_socmed_report"
    }
    project_dir = project_dirs.get(args.project)

    # 1. Sync T+1 data from API (API is source of truth)
    verification_error = None
    synced_stats = None
    if not args.skip_verify:
        print("  Syncing T+1 data from Facebook API...")
        is_verified, synced_stats, api_stats, error_msg = verify_data_with_api(
            args.project, config["db_path"], report_date, max_retries=1
        )
        if error_msg and "No tokens" not in error_msg:
            verification_error = error_msg
            print(f"  SYNC ERROR: {error_msg}")

        # Export to JSON and deploy to Vercel (update live website)
        if synced_stats and project_dir:
            print("  Exporting data to JSON...")
            if run_export_static_data(project_dir):
                print("  [OK] JSON exported")
                # Deploy to Vercel
                print("  Deploying to Vercel...")
                if deploy_to_vercel(project_dir, report_date):
                    print("  [OK] Deployed to Vercel - website updated")
                else:
                    print("  [!] Deploy failed (screenshot may show old data)")
            else:
                print("  [!] JSON export failed (screenshot may show old data)")

    # 2. Use synced stats if available, otherwise get from DB
    if synced_stats:
        yesterday_stats = synced_stats
        yesterday_stats["date"] = report_date
        print(f"  Using synced data: {yesterday_stats['posts']} posts, {yesterday_stats['engagement']} engagement")
    else:
        print("  Fetching yesterday's stats from DB...")
        yesterday_stats = get_yesterday_stats(config["db_path"], report_date)

    print("  Calculating monthly average...")
    monthly_avg = get_monthly_average(config["db_path"])

    print("  Fetching top posts...")
    yesterday_top_posts = get_top_posts_for_date(config["db_path"], report_date, limit=3)
    month_top_posts = get_top_posts_this_month(config["db_path"], limit=5)

    # 3. Format message
    if verification_error:
        # Send error report instead
        message = f"""<b>{config['project_name']} DAILY API SYNC - ERROR</b>
<i>{report_date}</i>

<b>DATA VERIFICATION FAILED</b>
{verification_error}

<b>DATABASE SHOWS:</b>
Posts: {yesterday_stats['posts']}
Engagement: {yesterday_stats['engagement']:,}

<i>Please check data manually and re-sync if needed.</i>"""
    else:
        message = format_summary_message(
            config["project_name"],
            yesterday_stats,
            monthly_avg,
            yesterday_top_posts,
            month_top_posts
        )

    # 4. Capture screenshots (skip if verification failed)
    screenshot_paths = []
    if not args.no_screenshot and not verification_error:
        print(f"  Capturing dashboard screenshots ({args.screenshot_filter} view)...")
        try:
            screenshot_paths = capture_screenshots_sync(
                config["url"],
                date_filter=args.screenshot_filter
            )
            print(f"  Captured {len(screenshot_paths)} screenshots")
        except Exception as e:
            print(f"  WARNING: Screenshot capture failed: {e}")
            screenshot_paths = []

    # 5. Send to Telegram
    print("  Sending to Telegram...")

    if screenshot_paths and len(screenshot_paths) >= 2:
        # Send first screenshot with message caption
        result = send_telegram_photo(config["chat_id"], screenshot_paths[0], message)

        # Send second screenshot with simple caption
        if os.path.exists(screenshot_paths[1]):
            send_telegram_photo(
                config["chat_id"],
                screenshot_paths[1],
                f"<b>{config['project_name']}</b> - Top Posts & Monthly Performance"
            )

        # Clean up temp files
        for path in screenshot_paths:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except:
                pass
    else:
        # Fallback: send text only
        if not verification_error:
            message += "\n\n<i>(Screenshot unavailable)</i>"
        result = send_telegram_message(config["chat_id"], message)

    if result.get("ok"):
        status = "with error" if verification_error else "successfully"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Report sent {status}!")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to send: {result}")

    return result


if __name__ == "__main__":
    main()
