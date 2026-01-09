@echo off
:: Run as Administrator

echo ============================================================
echo   Juan365 SocMed - Install Windows Service
echo ============================================================
echo.

:: Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Please run as Administrator!
    echo Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

set SERVICE_NAME=Juan365SocMedDaemon
set PYTHON_PATH=C:\Users\us\AppData\Local\Programs\Python\Python313\pythonw.exe
set SCRIPT_PATH=C:\Users\us\Desktop\juan365_socmed_report\juan365_daemon.py

echo Creating scheduled task...
echo.

:: Delete existing task if any
schtasks /delete /tn "%SERVICE_NAME%" /f >nul 2>&1

:: Create task that runs at startup
schtasks /create /tn "%SERVICE_NAME%" /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" /sc onstart /ru "%USERNAME%" /rl highest /f

if %errorLevel% equ 0 (
    echo.
    echo ============================================================
    echo   SUCCESS! Task created: %SERVICE_NAME%
    echo ============================================================
    echo.
    echo The daemon will start automatically on Windows startup.
    echo.
    echo To start now, run: start_daemon.bat
    echo To remove:         schtasks /delete /tn %SERVICE_NAME% /f
    echo.
) else (
    echo.
    echo ERROR: Failed to create task
)

pause
