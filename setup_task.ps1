# Setup Windows Task Scheduler for JuanBabes Daily Export
# Run this script as Administrator

$taskName = "JuanBabes Daily Export"
$batPath = "C:\Users\us\Desktop\juanbabes_project\daily_export.bat"
$workDir = "C:\Users\us\Desktop\juanbabes_project"

# Create action
$action = New-ScheduledTaskAction -Execute $batPath -WorkingDirectory $workDir

# Create trigger for 8:00 AM daily
$trigger = New-ScheduledTaskTrigger -Daily -At "8:00AM"

# Register the task
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Force

Write-Host ""
Write-Host "Task created successfully!" -ForegroundColor Green
Write-Host "Task Name: $taskName"
Write-Host "Schedule: Daily at 8:00 AM"
Write-Host ""
Write-Host "To run manually: schtasks /run /tn `"$taskName`""
