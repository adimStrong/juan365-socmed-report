@echo off
title Juan365 SocMed Push to Vercel
cd /d C:\Users\us\Desktop\juan365_socmed_report\frontend

echo ============================================================
echo PUSH TO VERCEL (Juan365 SocMed Report)
echo ============================================================
echo.

echo Deploying to Vercel...
vercel --prod --yes

echo.
echo ============================================================
echo PUSH COMPLETE
echo ============================================================
pause
