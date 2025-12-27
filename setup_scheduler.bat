@echo off
REM ============================================
REM Setup Windows Task Scheduler for Daily Export
REM Run this ONCE as Administrator to create the scheduled task
REM ============================================

echo Creating scheduled task: JuanBabes Daily Export at 8:00 AM...

schtasks /create /tn "JuanBabes Daily Export" /tr "C:\Users\us\Desktop\juanbabes_project\daily_export.bat" /sc daily /st 08:00 /f

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo SUCCESS! Task created.
    echo.
    echo Task Name: JuanBabes Daily Export
    echo Schedule: Daily at 8:00 AM
    echo Action: Run daily_export.bat
    echo ============================================
    echo.
    echo To view/modify: Open Task Scheduler ^> Task Scheduler Library
    echo To run now: schtasks /run /tn "JuanBabes Daily Export"
    echo To delete: schtasks /delete /tn "JuanBabes Daily Export" /f
    echo.
) else (
    echo.
    echo ERROR: Failed to create task. Try running as Administrator.
    echo Right-click this file ^> Run as administrator
    echo.
)

pause
