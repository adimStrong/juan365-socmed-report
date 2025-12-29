@echo off
title Juan365 Socmed - Hourly API Fetch
color 0A
cd /d C:\Users\us\Desktop\juan365_socmed_report

echo.
echo ============================================
echo Juan365 Socmed - Scheduled API Fetch
echo %date% %time%
echo ============================================
echo.

echo [1/3] Fetching missing posts from FB API...
python fetch_missing_posts.py
if %errorlevel% neq 0 (
    echo WARNING: API fetch failed - tokens may be expired
)

echo.
echo [2/3] Exporting analytics data...
python export_static_data.py

echo.
echo [3/3] Pushing to GitHub...
git add -A
git commit -m "Scheduled update: %date% %time%"
git push origin main

echo.
echo ============================================
echo DONE! Next run in 1 hour.
echo ============================================
echo.
pause
