# Instala as dependencias e cria o atalho de inicializacao com o Windows.
# Uso: powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { throw "Python nao encontrado. Instale o Python 3.10+ (python.org) e marque 'Add to PATH'." }

& $python -m pip install --user -r (Join-Path $here "requirements.txt")
& $python (Join-Path $here "tests\test_readonly.py")

$pythonw = Join-Path (Split-Path $python) "pythonw.exe"
$lnk = Join-Path ([Environment]::GetFolderPath("Startup")) "Attack Shark Battery.lnk"
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$s.TargetPath = $pythonw
$s.Arguments = "`"$(Join-Path $here 'x11_battery.pyw')`""
$s.WorkingDirectory = $here
$s.Save()
Start-Process $lnk
Write-Host "Pronto. O icone aparece perto do relogio e inicia junto com o Windows."
