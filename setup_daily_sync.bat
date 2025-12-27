@echo off
echo ============================================
echo JuanBabes - Setup Daily API Sync
echo ============================================
echo.
echo This will create a scheduled task to run at 8:00 AM daily.
echo.

REM Check if running as admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Please run this script as Administrator!
    echo Right-click this file and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo Creating scheduled task: JuanBabes Daily API Sync...
echo.

schtasks /create /tn "JuanBabes Daily API Sync" /tr "C:\Users\us\Desktop\juanbabes_project\daily_api_sync.bat" /sc daily /st 08:00 /f

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo SUCCESS! Scheduled task created.
    echo ============================================
    echo.
    echo Task Name: JuanBabes Daily API Sync
    echo Schedule:  Daily at 8:00 AM
    echo Action:    Run daily_api_sync.bat
    echo.
    echo To test now: schtasks /run /tn "JuanBabes Daily API Sync"
    echo To delete:   schtasks /delete /tn "JuanBabes Daily API Sync" /f
    echo.
) else (
    echo.
    echo ERROR: Failed to create scheduled task.
    echo.
)

pause
