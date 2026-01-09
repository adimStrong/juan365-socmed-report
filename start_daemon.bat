@echo off
title Juan365 SocMed Daemon
cd /d C:\Users\us\Desktop\juan365_socmed_report

echo ============================================================
echo JUAN365 SOCMED DAEMON
echo ============================================================
echo.
echo Schedule:
echo   - Every hour: Fetch API + notify new posts
echo   - At 6:00 AM: Export + push to Vercel
echo.
echo Press Ctrl+C to stop
echo ============================================================
echo.

python juan365_daemon.py

pause
