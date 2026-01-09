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

echo [1/7] Checking for scheduled reports (Daily/Monthly at 8am)...
python telegram_notifier.py

echo.
echo [2/7] Fetching missing posts from FB API...
python fetch_missing_posts.py

echo.
echo [3/7] Updating fan counts from FB API...
python update_fan_counts.py

echo.
echo [4/7] Checking for comment fetch (Daily at 7am)...
for /f "tokens=1 delims=:" %%a in ("%time%") do set hour=%%a
set hour=%hour: =%
if "%hour%"=="7" (
    echo Running daily comment fetch...
    python fetch_comments.py
) else (
    echo Skipping - comments only fetch at 7am
)

echo.
echo [5/7] Exporting analytics data...
python export_static_data.py

echo.
echo [6/7] Verifying data integrity...
python verify_data.py
if errorlevel 1 (
    echo.
    echo ERROR: Verification failed! Skipping push.
    pause
    goto LOOP
)

echo.
echo [7/7] Pushing to GitHub...
C:\Users\us\AppData\Local\Programs\Git\bin\git.exe add frontend/public/data/analytics.json
C:\Users\us\AppData\Local\Programs\Git\bin\git.exe commit -m "Scheduled update"
C:\Users\us\AppData\Local\Programs\Git\bin\git.exe push origin main

echo.
echo ============================================
echo DONE! Waiting 1 hour for next run...
echo Next run at approximately %time% + 1 hour
echo Press Ctrl+C to stop
echo ============================================
echo.

timeout /t 3600 /nobreak
goto LOOP
