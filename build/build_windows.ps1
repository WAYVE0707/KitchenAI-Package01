$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'Python Launcher (py) не найден.' }
if (-not (Get-Command iscc -ErrorAction SilentlyContinue)) { Write-Warning 'ISCC не найден. Установите Inno Setup или добавьте ISCC.exe в PATH.' }

py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller

if (Test-Path build\pyinstaller) { Remove-Item -Recurse -Force build\pyinstaller }
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
New-Item -ItemType Directory -Force dist | Out-Null

& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name KitchenAI src\app.py

if (-not (Test-Path dist\KitchenAI.exe)) { throw 'PyInstaller не создал KitchenAI.exe' }

if (Get-Command iscc -ErrorAction SilentlyContinue) {
    & iscc installer\KitchenAI.iss
    if (-not (Test-Path dist\KitchenAI_Setup.exe)) { throw 'Inno Setup не создал KitchenAI_Setup.exe' }
    Write-Host "DONE: $Root\dist\KitchenAI_Setup.exe"
} else {
    Write-Host "KitchenAI.exe создан. Установщик будет собран после установки Inno Setup."
}
