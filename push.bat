@echo off
title Juan365 Push to Vercel
cd /d C:\Users\us\Desktop\juan365_socmed_report

set GIT="C:\Users\us\AppData\Local\Programs\Git\bin\git.exe"

echo ============================================================
echo PUSH TO VERCEL (Juan365 SocMed)
echo ============================================================
echo.

echo [1/3] Adding changes...
%GIT% add -A

echo.
echo [2/3] Committing changes...
%GIT% commit -m "Update data - %date% %time%"

echo.
echo Pushing to GitHub...
%GIT% push origin main

echo.
echo ============================================================
echo [3/3] Deploying frontend to Vercel...
echo ============================================================
cd frontend
call npx vercel --prod --yes

echo.
echo ============================================================
echo DEPLOY COMPLETE
echo Live: https://juan365-socmed-report.vercel.app
echo ============================================================
pause
