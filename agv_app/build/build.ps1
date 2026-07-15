# build.ps1 - Build AGV_Analyzer thanh .exe (onedir)
#
# LY DO CO SCRIPT NAY:
#   PyInstaller loi khi duong dan du an chua ky tu co dau (vd "Du an CNTT").
#   Script tu dong build tai mot thu muc ASCII (%USERPROFILE%\agv_build) roi
#   chep ket qua ve thu muc dist cua du an.
#
# CACH DUNG (tu thu muc goc du an hoac bat ky dau):
#   powershell -ExecutionPolicy Bypass -File agv_app\build\build.ps1

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"

# Thu muc goc du an = cha cua 'agv_app' (PSScriptRoot = ...\agv_app\build)
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BuildRoot   = Join-Path $env:USERPROFILE "agv_build"

Write-Host "Project root : $ProjectRoot"
Write-Host "Build root   : $BuildRoot"

# 1. Chuan bi thu muc build ASCII
if (Test-Path $BuildRoot) { Remove-Item $BuildRoot -Recurse -Force }
New-Item -ItemType Directory -Path $BuildRoot | Out-Null
Copy-Item (Join-Path $ProjectRoot "agv_app") (Join-Path $BuildRoot "agv_app") -Recurse

# 2. Tao venv 3.8 + cai thu vien
Write-Host "== Tao venv Python 3.8 =="
py -3.8 -m venv (Join-Path $BuildRoot ".venv38")
$py = Join-Path $BuildRoot ".venv38\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -r (Join-Path $BuildRoot "agv_app\requirements.txt")

# 3. Build
Write-Host "== PyInstaller build =="
Push-Location $BuildRoot
& (Join-Path $BuildRoot ".venv38\Scripts\pyinstaller.exe") "agv_app\build\agv_app.spec" --noconfirm
Pop-Location

# 4. Chep ket qua ve du an
$srcDist = Join-Path $BuildRoot "dist\AGV_Analyzer"
$dstDist = Join-Path $ProjectRoot "dist\AGV_Analyzer"
if (Test-Path $dstDist) { Remove-Item $dstDist -Recurse -Force }
New-Item -ItemType Directory -Path (Split-Path $dstDist) -Force | Out-Null
Copy-Item $srcDist $dstDist -Recurse

Write-Host ""
Write-Host "HOAN TAT! App o: $dstDist\AGV_Analyzer.exe"
