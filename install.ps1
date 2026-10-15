# Run from source: installs the dependencies, runs the checks and starts the tray app.
# The language and "start with Windows" are asked on first run.
# Usage: powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { throw "Python not found. Install Python 3.10+ from python.org and tick 'Add to PATH'." }

& $python -m pip install --user -r (Join-Path $here "requirements.txt")
& $python (Join-Path $here "tests\test_readonly.py")
if ($LASTEXITCODE -ne 0) { throw "Read-only check failed." }

# v1.0 shortcut pointed to x11_battery.pyw (renamed): recreate it if it exists
$lnk = Join-Path ([Environment]::GetFolderPath("Startup")) "Attack Shark Battery.lnk"
$pythonw = Join-Path (Split-Path $python) "pythonw.exe"
$script = Join-Path $here "attackshark_battery_tray.pyw"
if (Test-Path $lnk) {
    $s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
    $s.TargetPath = $pythonw
    $s.Arguments = "`"$script`""
    $s.WorkingDirectory = $here
    $s.Save()
}
Start-Process $pythonw -ArgumentList "`"$script`"" -WorkingDirectory $here
Write-Host "Done. The battery icon appears next to the clock (or under the ^ arrow in the taskbar)."
