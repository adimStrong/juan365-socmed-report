@echo off
echo Starting JuanBabes Auto Sync Daemon...
echo This will sync automatically at 8:00 AM daily.
echo.
echo Keep this window open (or use start_auto_sync_hidden.vbs for hidden mode)
echo Press Ctrl+C to stop.
echo.
cd /d C:\Users\us\Desktop\juanbabes_project
python auto_sync_daemon.py
