@echo off
echo Stopping Juan365 SocMed Daemon...
taskkill /f /fi "WINDOWTITLE eq Juan365 SocMed Daemon" >nul 2>&1
taskkill /f /im pythonw.exe /fi "WINDOWTITLE eq *juan365*" >nul 2>&1
echo Done.
pause
