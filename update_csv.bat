@echo off
echo ============================================================
echo   Juan365 SocMed - Import Data from CSV Files
echo ============================================================
echo.
echo Place your CSV files in: csv_imports\
echo.

cd /d "%~dp0"

if not exist "csv_imports" (
    mkdir csv_imports
    echo Created csv_imports folder. Add your CSV files there.
    pause
    exit /b
)

echo Importing CSV data...
python csv_importer.py import-all

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
