"""
Juan365 Auto Sync Daemon
Runs in background and syncs at 8:00 AM daily

This daemon performs FULL sync including:
1. Posts sync (from Facebook API)
2. Follower counts update
3. Comment data fetch (self-comments vs organic)
4. Export static data

Usage:
    python auto_sync_daemon.py          # Run in foreground
    pythonw auto_sync_daemon.py         # Run hidden (no window)
    python auto_sync_daemon.py --now    # Run sync immediately

To auto-start on login:
    1. Press Win+R, type: shell:startup
    2. Create shortcut to: pythonw auto_sync_daemon.py
"""

import subprocess
import time
import os
import sys
from datetime import datetime, timedelta

PROJECT_DIR = r"C:\Users\us\Desktop\juan365_socmed_report"
SYNC_HOUR = 8  # 8 AM
SYNC_MINUTE = 0
SYNC_DAYS = 30  # Fetch last 30 days of posts (not just 7)

def show_notification(title, message):
    """Show Windows notification"""
    try:
        ps_command = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('{message}', '{title}', 'OK', 'Information')"
        subprocess.run(['powershell', '-Command', ps_command], capture_output=True)
    except:
        print(f"[NOTIFY] {title}: {message}")

def run_sync():
    """Run the FULL API sync including posts, followers, and comments"""
    os.chdir(PROJECT_DIR)
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting FULL sync...")
    print('='*60)

    try:
        # Step 1: Sync posts from Facebook API
        print("\n[1/5] Fetching posts from Facebook API...")
        subprocess.run(['python', 'scheduled_sync.py'], check=True)

        # Step 2: Update follower counts
        print("\n[2/5] Updating follower counts...")
        if os.path.exists('update_fan_counts.py'):
            subprocess.run(['python', 'update_fan_counts.py'], check=True)
        else:
            print("   (update_fan_counts.py not found, skipping)")

        # Step 3: Fetch comment data
        print("\n[3/5] Fetching comment data (self-comments)...")
        if os.path.exists('fetch_comments.py'):
            subprocess.run(['python', 'fetch_comments.py'], check=True)
        else:
            print("   (fetch_comments.py not found, skipping)")

        # Step 4: Export static data
        print("\n[4/5] Exporting analytics data...")
        if os.path.exists('export_static_data.py'):
            subprocess.run(['python', 'export_static_data.py'], check=True)
        else:
            print("   (export_static_data.py not found, skipping)")

        # Step 5: Git push if changes
        print("\n[5/5] Checking for changes to push...")
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)

        if result.stdout.strip():
            print("Changes detected, pushing to GitHub...")
            subprocess.run(['git', 'add', '-A'], check=True)
            subprocess.run(['git', 'commit', '-m', f'Daily full sync: {datetime.now().strftime("%Y-%m-%d %H:%M")}'], check=True)
            subprocess.run(['git', 'push', 'origin', 'main'], check=True)
            show_notification("Juan365 Daily Sync", "Full sync complete and deployed!")
            print("Push complete!")
        else:
            print("No changes detected.")
            show_notification("Juan365 Daily Sync", "Sync complete - no new data.")

        print(f"\n{'='*60}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] FULL SYNC COMPLETE!")
        print('='*60)

    except Exception as e:
        print(f"\nError during sync: {e}")
        show_notification("Juan365 Sync Error", str(e)[:100])

def get_seconds_until_next_sync():
    """Calculate seconds until next 8 AM"""
    now = datetime.now()
    target = now.replace(hour=SYNC_HOUR, minute=SYNC_MINUTE, second=0, microsecond=0)

    if now >= target:
        target += timedelta(days=1)

    return (target - now).total_seconds()

def main():
    # Check for --now flag to run immediately
    if "--now" in sys.argv:
        print("Running sync immediately...")
        run_sync()
        return

    print("="*60)
    print("Juan365 Auto Sync Daemon")
    print("="*60)
    print(f"Project: {PROJECT_DIR}")
    print(f"Sync scheduled for: {SYNC_HOUR:02d}:{SYNC_MINUTE:02d} daily")
    print(f"Tasks: Posts + Followers + Comments + Export")
    print("Press Ctrl+C to stop")
    print("="*60)

    show_notification("Juan365 Daemon Started", f"Will sync daily at {SYNC_HOUR}:00 AM")

    last_sync_date = None

    while True:
        now = datetime.now()
        today = now.date()

        # Check if it's sync time and we haven't synced today
        if now.hour == SYNC_HOUR and now.minute == SYNC_MINUTE and last_sync_date != today:
            run_sync()
            last_sync_date = today

        # Sleep for 30 seconds before checking again
        time.sleep(30)

if __name__ == "__main__":
    main()
