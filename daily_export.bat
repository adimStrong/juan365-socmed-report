@echo off
REM ============================================
REM JuanBabes Daily Export & Git Push
REM Runs at 8:00 AM daily via Task Scheduler
REM ============================================

cd /d C:\Users\us\Desktop\juanbabes_project

echo ============================================
echo JuanBabes Daily Export - %date% %time%
echo ============================================

REM Run the export script
echo Running export_static_data.py...
python export_static_data.py

REM Check if analytics.json was modified
git diff --quiet frontend/public/data/analytics.json
if %errorlevel% neq 0 (
    echo Changes detected, pushing to GitHub...
    git add frontend/public/data/analytics.json
    git commit -m "Daily update: %date% - Analytics data refresh"
    git push origin main
    echo Push complete!
) else (
    echo No changes detected, skipping push.
)

echo ============================================
echo Done! %time%
echo ============================================
