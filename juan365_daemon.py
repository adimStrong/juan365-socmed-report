"""
Juan365 SocMed Daemon
- Every hour: Fetch API + notify new posts
- At 6:00 AM: Export data + push to Vercel + send daily report

Usage:
    python juan365_daemon.py          # Run in foreground
    pythonw juan365_daemon.py         # Run hidden (no window)
"""

import subprocess
import sys
import time
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / "data" / "juan365_socmed.db"
STATE_FILE = PROJECT_DIR / "data" / "daemon_state.json"
PID_FILE = PROJECT_DIR / "data" / "daemon.pid"

# Schedule settings
PUSH_HOUR = 6  # 6 AM
PUSH_MINUTE = 0
CHECK_INTERVAL = 3600  # 1 hour in seconds

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {msg}")

def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"last_push_date": None, "notified_posts": []}

def save_state(state):
    STATE_FILE.parent.mkdir(exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def fetch_api():
    """Fetch last 7 days from Facebook API."""
    log("Fetching from Facebook API...")
    try:
        result = subprocess.run(
            [sys.executable, "fetch_missing_posts.py"],
            cwd=PROJECT_DIR,
            timeout=300
        )
        log("API fetch complete")
        return result.returncode == 0
    except Exception as e:
        log(f"API fetch error: {e}", "ERROR")
        return False

def get_recent_posts(hours=2):
    """Get posts PUBLISHED in the last N hours."""
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Convert local time to UTC for comparison (Philippines = UTC+8)
    local_now = datetime.now()
    utc_now = local_now - timedelta(hours=8)
    since_time_utc = (utc_now - timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M:%S')

    cursor.execute("""
        SELECT
            posts.post_id,
            p.page_name,
            posts.post_type,
            posts.title,
            posts.permalink,
            posts.publish_time
        FROM posts
        JOIN pages p ON posts.page_id = p.page_id
        WHERE posts.publish_time >= ?
        ORDER BY posts.publish_time DESC
    """, (since_time_utc,))

    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return posts

def notify_new_posts(posts, state):
    """Send Telegram notifications for new posts."""
    try:
        from telegram_notifier import send_new_post_alert
    except ImportError:
        log("telegram_notifier not found, skipping notifications", "WARN")
        return 0

    notified = state.get("notified_posts", [])
    new_count = 0

    for post in posts:
        post_id = post['post_id']
        if post_id in notified:
            continue

        log(f"Notifying: {post['page_name']} - {post['post_type']}")
        result = send_new_post_alert(
            page_name=post['page_name'],
            post_type=post['post_type'],
            title=post['title'],
            permalink=post['permalink'],
            publish_time=post['publish_time']
        )

        if result and result.get('ok'):
            notified.append(post_id)
            new_count += 1
            time.sleep(1)

    state["notified_posts"] = notified[-500:]
    return new_count

def export_data():
    """Export static JSON for frontend."""
    log("Exporting static data...")
    try:
        result = subprocess.run(
            [sys.executable, "export_static_data.py"],
            cwd=PROJECT_DIR,
            timeout=120
        )
        if result.returncode == 0:
            log("Export complete")
            return True
        else:
            log("Export failed", "ERROR")
            return False
    except Exception as e:
        log(f"Export error: {e}", "ERROR")
        return False

def push_to_vercel():
    """Push data to Vercel via CLI."""
    log("Pushing to Vercel...")
    try:
        result = subprocess.run(
            ["vercel", "--prod", "--yes"],
            cwd=PROJECT_DIR / "frontend",
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            log("Push complete!")
            return True
        else:
            log(f"Push error: {result.stderr[:200]}", "ERROR")
            return False

    except Exception as e:
        log(f"Push error: {e}", "ERROR")
        return False

def hourly_check(state):
    """Hourly task: Fetch API + notify new posts."""
    log("=" * 50)
    log("HOURLY CHECK")
    log("=" * 50)

    # Fetch from API
    fetch_api()

    # Get recent posts and notify
    recent_posts = get_recent_posts(hours=2)

    if recent_posts:
        log(f"Found {len(recent_posts)} posts in last 2 hours")
        new_count = notify_new_posts(recent_posts, state)
        if new_count > 0:
            log(f"Sent {new_count} new notification(s)")
        else:
            log("All posts already notified")
    else:
        log("No new posts")

    save_state(state)

def daily_push(state):
    """Daily task at 6am: Sync API, Export, Deploy, Send Report with Screenshot."""
    log("=" * 50)
    log("6AM DAILY PUSH")
    log("=" * 50)

    state["last_push_date"] = datetime.now().strftime('%Y-%m-%d')
    save_state(state)

    # Use send_daily_report_v2.py which handles:
    # 1. API sync (T+1 data verification)
    # 2. Export to JSON
    # 3. Deploy to Vercel
    # 4. Take dashboard screenshots
    # 5. Send to Telegram
    try:
        log("Running daily report v2 (sync + export + deploy + screenshot)...")
        result = subprocess.run(
            [sys.executable, "send_daily_report_v2.py", "--project", "juan365", "--screenshot-filter", "thismonth"],
            cwd=PROJECT_DIR,
            timeout=300  # 5 minutes for screenshot capture
        )
        if result.returncode == 0:
            log("Daily report sent!")
        else:
            log("Daily report may have issues", "WARN")
    except Exception as e:
        log(f"Daily report error: {e}", "ERROR")

def check_already_running():
    """Check if daemon is already running using PID file."""
    import os
    if PID_FILE.exists():
        try:
            with open(PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            # Check if process is still running (Windows)
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, old_pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if handle:
                kernel32.CloseHandle(handle)
                return True, old_pid
        except:
            pass
    return False, None

def write_pid():
    """Write current PID to file."""
    import os
    PID_FILE.parent.mkdir(exist_ok=True)
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

def cleanup_pid():
    """Remove PID file on exit."""
    try:
        PID_FILE.unlink()
    except:
        pass

def main():
    # Check if already running
    running, old_pid = check_already_running()
    if running:
        print(f"ERROR: Daemon already running (PID: {old_pid})")
        print("Close the other daemon window first, or delete:")
        print(f"  {PID_FILE}")
        input("Press Enter to exit...")
        return

    # Write PID file
    write_pid()
    import atexit
    atexit.register(cleanup_pid)

    print("=" * 50)
    print("JUAN365 SOCMED DAEMON")
    print("=" * 50)
    print(f"Project: {PROJECT_DIR}")
    print(f"Schedule:")
    print(f"  - Every hour: Fetch API + notify new posts")
    print(f"  - At {PUSH_HOUR:02d}:{PUSH_MINUTE:02d}: Export + push to Vercel")
    print("Press Ctrl+C to stop")
    print("=" * 50)

    state = load_state()
    last_hourly_check = None

    # Run initial check
    hourly_check(state)
    last_hourly_check = datetime.now()
    next_check = last_hourly_check + timedelta(seconds=CHECK_INTERVAL)
    log(f"Next check at: {next_check.strftime('%H:%M:%S')}")
    log("-" * 50)

    while True:
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')

        # Check for 6am push
        if (now.hour == PUSH_HOUR and
            now.minute >= PUSH_MINUTE and
            now.minute < PUSH_MINUTE + 5 and
            state.get("last_push_date") != today):
            daily_push(state)

        # Check for hourly task
        if last_hourly_check is None or (now - last_hourly_check).total_seconds() >= CHECK_INTERVAL:
            hourly_check(state)
            last_hourly_check = now
            next_check = now + timedelta(seconds=CHECK_INTERVAL)
            log(f"Next check at: {next_check.strftime('%H:%M:%S')}")
            log("-" * 50)

        # Sleep for 30 seconds
        time.sleep(30)

if __name__ == "__main__":
    main()
