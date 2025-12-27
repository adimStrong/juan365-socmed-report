"""
JuanBabes Auto Sync Daemon
Runs in background and syncs at 8:00 AM daily

Usage:
    python auto_sync_daemon.py          # Run in foreground
    pythonw auto_sync_daemon.py         # Run hidden (no window)

To auto-start on login:
    1. Press Win+R, type: shell:startup
    2. Create shortcut to: pythonw auto_sync_daemon.py
"""

import subprocess
import time
import os
from datetime import datetime, timedelta

PROJECT_DIR = r"C:\Users\us\Desktop\juanbabes_project"
SYNC_HOUR = 8  # 8 AM
SYNC_MINUTE = 0

def show_notification(title, message):
    """Show Windows notification"""
    try:
        ps_command = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('{message}', '{title}', 'OK', 'Information')"
        subprocess.run(['powershell', '-Command', ps_command], capture_output=True)
    except:
        print(f"[NOTIFY] {title}: {message}")

def run_sync():
    """Run the API sync and export"""
    os.chdir(PROJECT_DIR)
    print(f"\n{'='*50}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting sync...")
    print('='*50)

    try:
        # Step 1: Sync from Facebook API
        print("[1/3] Fetching from Facebook API...")
        subprocess.run(['python', 'scheduled_sync.py'], check=True)

        # Step 2: Export static data
        print("[2/3] Exporting analytics...")
        subprocess.run(['python', 'export_static_data.py'], check=True)

        # Step 3: Git push if changes
        print("[3/3] Checking for changes...")
        result = subprocess.run(['git', 'diff', '--quiet', 'frontend/public/data/analytics.json'])

        if result.returncode != 0:
            print("Changes detected, pushing to GitHub...")
            subprocess.run(['git', 'add', 'frontend/public/data/analytics.json'], check=True)
            subprocess.run(['git', 'commit', '-m', f'Daily API sync: {datetime.now().strftime("%Y-%m-%d")}'], check=True)
            subprocess.run(['git', 'push', 'origin', 'main'], check=True)
            show_notification("JuanBabes Daily Sync", "API data synced and deployed!")
            print("Push complete!")
        else:
            print("No changes detected.")
            show_notification("JuanBabes Daily Sync", "No new data to sync.")

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Sync complete!")

    except Exception as e:
        print(f"Error during sync: {e}")
        show_notification("JuanBabes Sync Error", str(e)[:100])

def get_seconds_until_next_sync():
    """Calculate seconds until next 8 AM"""
    now = datetime.now()
    target = now.replace(hour=SYNC_HOUR, minute=SYNC_MINUTE, second=0, microsecond=0)

    if now >= target:
        target += timedelta(days=1)

    return (target - now).total_seconds()

def main():
    print("="*50)
    print("JuanBabes Auto Sync Daemon")
    print("="*50)
    print(f"Sync scheduled for: {SYNC_HOUR:02d}:{SYNC_MINUTE:02d} daily")
    print("Press Ctrl+C to stop")
    print("="*50)

    show_notification("JuanBabes Daemon Started", f"Will sync daily at {SYNC_HOUR}:00 AM")

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
