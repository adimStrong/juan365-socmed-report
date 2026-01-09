@echo off
echo ============================================================
echo   Juan365 SocMed - Fetch Data from Facebook API
echo ============================================================
echo.

cd /d "%~dp0"

echo Fetching posts from Facebook API...
python fetch_missing_posts.py --no-notify

echo.
echo ============================================================
echo   Rebuilding static data for frontend...
echo ============================================================
python export_static_data.py

echo.
echo ============================================================
echo   Done! Data updated from API.
echo ============================================================
pause
