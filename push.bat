@echo off
title Juan365 Push to Vercel
cd /d C:\Users\us\Desktop\juan365_socmed_report

set GIT="C:\Users\us\AppData\Local\Programs\Git\bin\git.exe"

echo ============================================================
echo PUSH TO VERCEL (Juan365 SocMed)
echo ============================================================
echo.

echo [1/5] Cleaning up duplicates...
python cleanup_duplicates.py

echo.
echo [2/5] Exporting data...
python export_static_data.py

echo.
echo [3/5] Adding changes...
%GIT% add -A

echo.
echo [4/5] Committing and pushing to GitHub...
%GIT% commit -m "Update data - %date% %time%"
%GIT% push origin main

echo.
echo ============================================================
echo [5/5] Deploying frontend to Vercel...
echo ============================================================
REM Run from project root (not frontend) to avoid path issues
call npx vercel --prod --yes --force

echo.
echo ============================================================
echo DEPLOY COMPLETE
echo Live: https://juan365-socmed-report.vercel.app
echo ============================================================
pause
