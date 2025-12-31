@echo off
title Juan365 Socmed - Hourly API Fetch
color 0A
cd /d C:\Users\us\Desktop\juan365_socmed_report

:LOOP
echo.
echo ============================================
echo Juan365 Socmed - Scheduled API Fetch
echo %date% %time%
echo ============================================
echo.

echo [1/4] Checking for scheduled reports (Daily/Monthly)...
python telegram_notifier.py

echo.
echo [2/4] Fetching missing posts from FB API...
python fetch_missing_posts.py

echo.
echo [3/4] Exporting analytics data...
python export_static_data.py

echo.
echo [4/4] Pushing to GitHub...
C:\Users\us\AppData\Local\Programs\Git\bin\git.exe add frontend/public/data/analytics.json
C:\Users\us\AppData\Local\Programs\Git\bin\git.exe commit -m "Scheduled update"
C:\Users\us\AppData\Local\Programs\Git\bin\git.exe push origin main

echo.
echo ============================================
echo DONE\! Waiting 1 hour for next run...
echo Next run at approximately %time% + 1 hour
echo Press Ctrl+C to stop
echo ============================================
echo.

timeout /t 3600 /nobreak
goto LOOP
