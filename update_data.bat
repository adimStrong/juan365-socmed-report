@echo off
title Juan365 Socmed - Update Data
color 0A
cd /d C:\Users\us\Desktop\juan365_socmed_report

:MENU
echo.
echo ============================================================
echo Juan365 Socmed Data Update Tool
echo ============================================================
echo.
echo   [1] CSV Import (Meta exports) + Export + Push
echo   [2] API Fetch (posts + comments) + Export + Push
echo   [3] Exit
echo.
set /p choice="Enter choice (1-3): "

if "%choice%"=="1" goto CSV_UPDATE
if "%choice%"=="2" goto API_UPDATE
if "%choice%"=="3" goto END
echo Invalid choice. Try again.
goto MENU

:CSV_UPDATE
echo.
echo ============================================================
echo [1/3] CSV IMPORT - Importing from manual exports...
echo ============================================================
dir /b "exports\from content manual Export\*.csv" 2>nul
echo.
python import_manual_exports.py
if errorlevel 1 (
    echo ERROR: CSV import failed
    pause
    goto MENU
)

echo.
echo ============================================================
echo [2/3] EXPORT - Generating JSON for frontend...
echo ============================================================
python export_static_data.py

echo.
echo ============================================================
echo [3/3] PUSH - Committing and pushing to GitHub...
echo ============================================================
set GIT="C:\Users\us\AppData\Local\Programs\Git\bin\git.exe"
%GIT% add -A
%GIT% commit -m "CSV update - %date%"
%GIT% push origin main

echo.
echo ============================================================
echo DONE! CSV update complete.
echo ============================================================
pause
goto MENU

:API_UPDATE
echo.
echo ============================================================
echo [1/4] API FETCH - Fetching missing posts...
echo ============================================================
python fetch_missing_posts.py

echo.
echo ============================================================
echo [2/4] API FETCH - Fetching comments (10 workers)...
echo ============================================================
python fetch_comments.py --workers 10

echo.
echo ============================================================
echo [3/4] EXPORT - Generating JSON for frontend...
echo ============================================================
python export_static_data.py

echo.
echo ============================================================
echo [4/4] PUSH - Committing and pushing to GitHub...
echo ============================================================
set GIT="C:\Users\us\AppData\Local\Programs\Git\bin\git.exe"
%GIT% add -A
%GIT% commit -m "API update - %date%"
%GIT% push origin main

echo.
echo ============================================================
echo DONE! API update complete.
echo ============================================================
pause
goto MENU

:END
echo Goodbye!
exit /b
