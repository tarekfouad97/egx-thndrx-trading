# EGX ThndrX Trading - Windows bootstrap: installs Python 3 if missing, then runs install.py.
#   Right-click > Run with PowerShell, or double-click Install-Windows.bat
param([switch]$Yes)
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Get-Py {
  foreach ($c in @("py -3", "python", "python3")) {
    try {
      $v = & cmd /c "$c -c ""import sys;print(1 if sys.version_info>=(3,9) else 0)""" 2>$null
      if ($v -eq "1") { return $c }
    } catch {}
  }
  return $null
}

$py = Get-Py
if (-not $py) {
  Write-Host "Python 3.9+ not found - installing Python 3.12 with winget..."
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
  } else {
    $url = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
    $exe = "$env:TEMP\python-3.12.7-amd64.exe"
    Invoke-WebRequest -Uri $url -OutFile $exe
    Start-Process -FilePath $exe -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1" -Wait
  }
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
  $py = Get-Py
  if (-not $py) { Write-Host "Python installed - please close this window and run the installer again."; exit 1 }
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  $a = Read-Host "Node.js is optional (MP4 recap, design skills). Install it with winget now? [y/N]"
  if ($a -match "^[Yy]") { winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements }
}

$args2 = @("install.py")
if ($Yes) { $args2 += "--yes" }
& cmd /c "$py $($args2 -join ' ')"
