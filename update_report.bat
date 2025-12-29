@echo off
color 0A
title JUAN365 SOCMED REPORT - UPDATE
cd /d C:\Users\us\Desktop\juan365_socmed_report

echo.
echo ============================================
echo Juan365 Socmed Report Update - %date% %time%
echo ============================================
echo.
echo Workflow: CSV data is PRIORITY (has views/reach)
echo           FB API fills gaps for missing dates
echo ============================================
echo.

REM Step 1: Import all CSVs from manual export folder
echo [1/5] Importing CSV data (priority)...
python csv_importer.py import-all "exports\from content manual Export" --mode merge
if %errorlevel% neq 0 (
    echo ERROR: CSV import failed!
    pause
    exit /b 1
)

REM Step 2: Fetch missing posts from FB API
echo.
echo [2/5] Fetching missing posts from FB API (fills gaps)...
python fetch_missing_posts.py
if %errorlevel% neq 0 (
    echo WARNING: Missing posts fetch failed (tokens may be expired)
)

REM Step 3: Export static data for frontend
echo.
echo [3/5] Exporting analytics data...
python export_static_data.py
if %errorlevel% neq 0 (
    echo ERROR: Export failed!
    pause
    exit /b 1
)

REM Step 4: Git commit and push
echo.
echo [4/5] Pushing to GitHub...
git add -A
git commit -m "Report update: %date% - CSV import and analytics refresh"
git push origin main
if %errorlevel% neq 0 (
    echo WARNING: Git push may have failed. Retrying...
    git push origin main
)

REM Step 5: Notify user
echo.
echo [5/5] Complete!
echo.
echo ============================================
echo DONE! Socmed Report updated and pushed.
echo ============================================
echo.

powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Socmed Report updated!', 'Juan365 Update Complete', 'OK', 'Information')" >nul 2>&1

pause
