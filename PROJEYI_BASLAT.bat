@echo off
chcp 65001 >nul
title AY INIS YERI NAVIGATORU 3D - Sunucu
cd /d "%~dp0"

echo ==================================================================
echo   AY INIS YERI NAVIGATORU 3D BASLATILIYOR...
echo   Lutfen bekleyin, sunucu hazir oldugunda tarayici otomatik acilacak.
echo ==================================================================

REM Eger 8000 portunda acik kalmis eski bir sunucu varsa temizle
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Sunucu hazir olur olmaz tarayiciyi otomatik olarak ac (arka planda)
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "for ($i=0; $i -lt 40; $i++) { Start-Sleep -Milliseconds 500; try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/sites' -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { break } } catch {} }; Start-Process 'http://127.0.0.1:8000'"

REM Python sunucusunu baslat
if exist "C:\Users\acer\AppData\Local\Python\bin\python.exe" (
    "C:\Users\acer\AppData\Local\Python\bin\python.exe" app.py
) else (
    python app.py
)

echo.
echo Sunucu durduruldu. Cikmak icin bir tusa basin...
pause >nul
