$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Write-Host "== Building frontend =="
Set-Location "$Root/frontend"
npm ci
npm run build

Write-Host "== Building backend (PyInstaller) =="
Set-Location "$Root/backend"
if (!(Test-Path ".venv")) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1
pip install -r requirements-build.txt
pyinstaller pyinstaller_backend.spec --noconfirm --clean

Write-Host "== Building Electron installer =="
Set-Location "$Root/desktop"
npm ci
npm run dist:win

Write-Host "== Copying installer to exe/ =="
$ExeDir = "$Root/exe"
New-Item -ItemType Directory -Force -Path $ExeDir | Out-Null
Get-ChildItem "$Root/desktop/dist/*.exe" | ForEach-Object {
  Copy-Item $_.FullName -Destination $ExeDir -Force
  Write-Host "Copied $($_.Name) to exe/"
}
Write-Host "Done."
