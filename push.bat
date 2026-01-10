@echo off
title Juan365 Push to Vercel (via GitHub)
cd /d C:\Users\us\Desktop\juan365_socmed_report

set GIT="C:\Users\us\AppData\Local\Programs\Git\bin\git.exe"

echo ============================================================
echo PUSH TO VERCEL (Juan365 SocMed) via GitHub
echo ============================================================
echo.

echo Adding changes...
%GIT% add -A

echo.
echo Committing changes...
%GIT% commit -m "Update data - %date% %time%"

echo.
echo Pushing to GitHub (auto-deploys to Vercel)...
%GIT% push origin main

echo.
echo ============================================================
echo PUSH COMPLETE
echo Vercel will auto-deploy from GitHub.
echo Live: https://juan365-socmed-report.vercel.app
echo ============================================================
pause
