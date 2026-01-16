@echo off
echo ============================================================
echo   Juan365 SocMed - Import Data from CSV Files
echo ============================================================
echo.
echo Place your CSV files in: exports\from content manual Export\
echo.

cd /d "%~dp0"

if not exist "exports\from content manual Export" (
    mkdir "exports\from content manual Export"
    echo Created exports\from content manual Export folder. Add your CSV files there.
    pause
    exit /b
)

echo Importing CSV data...
python csv_importer.py import-all "exports\from content manual Export"

echo.
echo ============================================================
echo   Rebuilding static data for frontend...
echo ============================================================
python export_static_data.py

echo.
echo ============================================================
echo   Done! Data imported from CSV.
echo ============================================================
pause
