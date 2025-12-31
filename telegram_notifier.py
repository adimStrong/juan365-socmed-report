"""
Telegram Notifier for Juan365 Socmed Report
Sends daily/monthly reports and new post alerts to Telegram group
"""

import requests
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Telegram Configuration
BOT_TOKEN = "8528398122:AAG9o7TOPrGxMEv_1eDIoiMO1cvTYq4Um7s"
CHAT_ID = "-5118984778"  # Socmed FB notification group

# Database path
DB_PATH = Path(__file__).parent / "data" / "juan365_socmed.db"

def send_message(text, parse_mode="HTML"):
    """Send a message to the Telegram group."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Telegram error: {e}")
        return None

def get_time_ago(publish_time_str):
    """Convert publish time to 'X mins ago' or 'X hrs ago' format."""
    try:
        # Handle various datetime formats
        if 'T' in publish_time_str:
            publish_time = datetime.fromisoformat(publish_time_str.replace('Z', '+00:00').split('+')[0])
        else:
            publish_time = datetime.strptime(publish_time_str, '%Y-%m-%d %H:%M:%S')

        now = datetime.now()
        diff = now - publish_time
        total_seconds = int(diff.total_seconds())

        if total_seconds < 0:
            return "just now"
        elif total_seconds < 60:
            return f"{total_seconds} secs ago"
        elif total_seconds < 3600:
            mins = total_seconds // 60
            return f"{mins} min{'s' if mins > 1 else ''} ago"
        elif total_seconds < 86400:
            hrs = total_seconds // 3600
            return f"{hrs} hr{'s' if hrs > 1 else ''} ago"
        else:
            days = total_seconds // 86400
            return f"{days} day{'s' if days > 1 else ''} ago"
    except:
        return "recently"

def get_post_type_display(post_type):
    """Combine Video/Reels into one category."""
    if post_type in ['Videos', 'Reels', 'Video', 'Reel']:
        return 'Video/Reels'
    return post_type or 'Post'

def send_new_post_alert(page_name, post_type, title, permalink, publish_time):
    """Send alert for a new post detected."""
    time_ago = get_time_ago(publish_time)
    post_type_display = get_post_type_display(post_type)

    # Truncate title if too long
    title_display = (title[:100] + "...") if title and len(title) > 100 else (title or "No caption")

    message = f"""
<b>NEW POST DETECTED</b>

<b>Page:</b> {page_name}
<b>Type:</b> {post_type_display}
<b>Posted:</b> {time_ago}

<b>Caption:</b>
{title_display}

<a href="{permalink}">View Post</a>
"""
    return send_message(message.strip())

def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def send_daily_report():
    """Send daily report at 8am."""
    conn = get_db_connection()
    cursor = conn.cursor()

    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')

    # Get yesterday's stats
    cursor.execute("""
        SELECT
            COUNT(*) as post_count,
            COALESCE(SUM(reactions_total), 0) as total_reactions,
            COALESCE(SUM(comments_count), 0) as total_comments,
            COALESCE(SUM(shares_count), 0) as total_shares,
            COALESCE(SUM(total_engagement), 0) as total_engagement
        FROM posts
        WHERE DATE(publish_time) = ?
    """, (yesterday,))
    yesterday_stats = cursor.fetchone()

    # Get this month's stats
    this_month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT
            COUNT(*) as post_count,
            COALESCE(SUM(total_engagement), 0) as total_engagement,
            COUNT(DISTINCT DATE(publish_time)) as days_with_posts
        FROM posts
        WHERE DATE(publish_time) >= ?
    """, (this_month_start,))
    this_month = cursor.fetchone()

    # Get last month's stats for comparison
    last_month_end = (datetime.now().replace(day=1) - timedelta(days=1))
    last_month_start = last_month_end.replace(day=1).strftime('%Y-%m-%d')
    last_month_end_str = last_month_end.strftime('%Y-%m-%d')

    cursor.execute("""
        SELECT
            COUNT(*) as post_count,
            COALESCE(SUM(total_engagement), 0) as total_engagement
        FROM posts
        WHERE DATE(publish_time) BETWEEN ? AND ?
    """, (last_month_start, last_month_end_str))
    last_month = cursor.fetchone()

    # Get page breakdown for yesterday
    cursor.execute("""
        SELECT
            p.page_name,
            COUNT(*) as post_count,
            COALESCE(SUM(posts.reactions_total), 0) as reactions,
            COALESCE(SUM(posts.comments_count), 0) as comments,
            COALESCE(SUM(posts.shares_count), 0) as shares,
            COALESCE(SUM(posts.total_engagement), 0) as engagement
        FROM posts
        JOIN pages p ON posts.page_id = p.page_id
        WHERE DATE(posts.publish_time) = ?
        GROUP BY p.page_name
        ORDER BY engagement DESC
    """, (yesterday,))
    page_breakdown = cursor.fetchall()

    # Get top 5 posts yesterday
    cursor.execute("""
        SELECT
            p.page_name,
            posts.title,
            posts.post_type,
            posts.total_engagement,
            posts.permalink
        FROM posts
        JOIN pages p ON posts.page_id = p.page_id
        WHERE DATE(posts.publish_time) = ?
        ORDER BY posts.total_engagement DESC
        LIMIT 5
    """, (yesterday,))
    top_posts = cursor.fetchall()

    conn.close()

    # Calculate month comparison
    if last_month['total_engagement'] > 0:
        month_change = ((this_month['total_engagement'] - last_month['total_engagement']) / last_month['total_engagement']) * 100
        month_change_str = f"+{month_change:.1f}%" if month_change >= 0 else f"{month_change:.1f}%"
    else:
        month_change_str = "N/A"

    # Calculate daily average
    days_with_posts = this_month['days_with_posts'] or 1
    daily_avg = this_month['total_engagement'] / days_with_posts

    if daily_avg > 0:
        vs_avg = ((yesterday_stats['total_engagement'] - daily_avg) / daily_avg) * 100
        vs_avg_str = f"+{vs_avg:.1f}%" if vs_avg >= 0 else f"{vs_avg:.1f}%"
    else:
        vs_avg_str = "N/A"

    # Build message
    message = f"""
<b>DAILY REPORT - {yesterday}</b>

<b>YESTERDAY'S SUMMARY</b>
Posts: {yesterday_stats['post_count']}
Reactions: {yesterday_stats['total_reactions']:,}
Comments: {yesterday_stats['total_comments']:,}
Shares: {yesterday_stats['total_shares']:,}
Total Engagement: {yesterday_stats['total_engagement']:,}

<b>vs This Month Avg:</b> {vs_avg_str}

<b>PAGE BREAKDOWN</b>
"""

    for page in page_breakdown:
        message += f"• {page['page_name']}: {page['post_count']} posts, {page['engagement']:,} eng\n"

    if not page_breakdown:
        message += "No posts yesterday\n"

    message += f"""
<b>MONTHLY OVERVIEW</b>
This Month: {this_month['total_engagement']:,} engagement
Last Month: {last_month['total_engagement']:,} engagement
Change: {month_change_str}

<b>TOP 5 POSTS YESTERDAY</b>
"""

    for i, post in enumerate(top_posts, 1):
        title_short = (post['title'][:30] + "...") if post['title'] and len(post['title']) > 30 else (post['title'] or "No caption")
        post_type_display = get_post_type_display(post['post_type'])
        message += f"{i}. [{post_type_display}] {title_short} - {post['total_engagement']:,} eng\n"

    if not top_posts:
        message += "No posts yesterday\n"

    return send_message(message.strip())

def send_monthly_report():
    """Send monthly report on the 1st of each month."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get last month's date range
    today = datetime.now()
    last_month_end = (today.replace(day=1) - timedelta(days=1))
    last_month_start = last_month_end.replace(day=1)
    last_month_name = last_month_start.strftime('%B %Y')

    # Previous month for comparison
    prev_month_end = (last_month_start - timedelta(days=1))
    prev_month_start = prev_month_end.replace(day=1)

    # Get last month's stats
    cursor.execute("""
        SELECT
            COUNT(*) as post_count,
            COALESCE(SUM(reactions_total), 0) as total_reactions,
            COALESCE(SUM(comments_count), 0) as total_comments,
            COALESCE(SUM(shares_count), 0) as total_shares,
            COALESCE(SUM(views_count), 0) as total_views,
            COALESCE(SUM(total_engagement), 0) as total_engagement
        FROM posts
        WHERE DATE(publish_time) BETWEEN ? AND ?
    """, (last_month_start.strftime('%Y-%m-%d'), last_month_end.strftime('%Y-%m-%d')))
    month_stats = cursor.fetchone()

    # Get previous month's stats
    cursor.execute("""
        SELECT
            COUNT(*) as post_count,
            COALESCE(SUM(total_engagement), 0) as total_engagement
        FROM posts
        WHERE DATE(publish_time) BETWEEN ? AND ?
    """, (prev_month_start.strftime('%Y-%m-%d'), prev_month_end.strftime('%Y-%m-%d')))
    prev_month = cursor.fetchone()

    # Get page ranking
    cursor.execute("""
        SELECT
            p.page_name,
            COUNT(*) as post_count,
            COALESCE(SUM(posts.total_engagement), 0) as engagement
        FROM posts
        JOIN pages p ON posts.page_id = p.page_id
        WHERE DATE(posts.publish_time) BETWEEN ? AND ?
        GROUP BY p.page_name
        ORDER BY engagement DESC
    """, (last_month_start.strftime('%Y-%m-%d'), last_month_end.strftime('%Y-%m-%d')))
    page_ranking = cursor.fetchall()

    # Get top 10 posts
    cursor.execute("""
        SELECT
            p.page_name,
            posts.title,
            posts.post_type,
            posts.total_engagement,
            posts.permalink
        FROM posts
        JOIN pages p ON posts.page_id = p.page_id
        WHERE DATE(posts.publish_time) BETWEEN ? AND ?
        ORDER BY posts.total_engagement DESC
        LIMIT 10
    """, (last_month_start.strftime('%Y-%m-%d'), last_month_end.strftime('%Y-%m-%d')))
    top_posts = cursor.fetchall()

    conn.close()

    # Calculate growth
    if prev_month['total_engagement'] > 0:
        growth = ((month_stats['total_engagement'] - prev_month['total_engagement']) / prev_month['total_engagement']) * 100
        growth_str = f"+{growth:.1f}%" if growth >= 0 else f"{growth:.1f}%"
    else:
        growth_str = "N/A"

    # Build message
    message = f"""
<b>MONTHLY REPORT - {last_month_name}</b>

<b>OVERALL STATS</b>
Total Posts: {month_stats['post_count']}
Total Reactions: {month_stats['total_reactions']:,}
Total Comments: {month_stats['total_comments']:,}
Total Shares: {month_stats['total_shares']:,}
Total Views: {month_stats['total_views']:,}
Total Engagement: {month_stats['total_engagement']:,}

<b>vs Previous Month:</b> {growth_str}

<b>PAGE RANKING</b>
"""

    for i, page in enumerate(page_ranking, 1):
        medal = ["1.", "2.", "3."][i-1] if i <= 3 else f"{i}."
        message += f"{medal} {page['page_name']}: {page['post_count']} posts, {page['engagement']:,} eng\n"

    message += f"""
<b>TOP 10 POSTS</b>
"""

    for i, post in enumerate(top_posts, 1):
        title_short = (post['title'][:25] + "...") if post['title'] and len(post['title']) > 25 else (post['title'] or "No caption")
        post_type_display = get_post_type_display(post['post_type'])
        message += f"{i}. [{post_type_display}] {title_short} - {post['total_engagement']:,}\n"

    return send_message(message.strip())

def should_send_daily_report():
    """Check if it's time to send daily report (8 AM)."""
    now = datetime.now()
    return now.hour == 8 and now.minute < 5

def should_send_monthly_report():
    """Check if it's time to send monthly report (1st of month at 8 AM)."""
    now = datetime.now()
    return now.day == 1 and now.hour == 8 and now.minute < 5

def check_and_send_reports():
    """Check time and send appropriate reports."""
    if should_send_monthly_report():
        print("Sending monthly report...")
        send_monthly_report()
    elif should_send_daily_report():
        print("Sending daily report...")
        send_daily_report()

# Test function
def test_connection():
    """Test Telegram connection."""
    result = send_message("Test message from Juan365 Socmed Analytics Bot")
    if result and result.get('ok'):
        print("Telegram connection successful!")
        return True
    else:
        print(f"Telegram connection failed: {result}")
        return False

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "test":
            test_connection()
        elif command == "daily":
            send_daily_report()
        elif command == "monthly":
            send_monthly_report()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python telegram_notifier.py [test|daily|monthly]")
    else:
        print("Checking for scheduled reports...")
        check_and_send_reports()
