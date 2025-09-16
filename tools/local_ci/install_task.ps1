param(
  [switch]$RunAgentsOnStart
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command Register-ScheduledTask -ErrorAction SilentlyContinue)) {
  throw 'This script requires ScheduledTasks module (Windows)'
}

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$StartScript = Join-Path $RepoRoot 'tools\local_ci\start.ps1'
$TaskName = 'IaClinique-LocalCI'

$args = "-NoLogo -NoProfile -File `"$StartScript`" -Watch -DebounceMs 1500"
if ($RunAgentsOnStart) { $args += ' -RunAgentsOnStart' }

$action = New-ScheduledTaskAction -Execute 'pwsh' -Argument $args -WorkingDirectory $RepoRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null

Write-Host "Installed Scheduled Task '$TaskName' (runs at logon)."
Write-Host "Command: pwsh $args"
Write-Host "WorkingDirectory: $RepoRoot"

