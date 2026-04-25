@echo off
chcp 65001 > nul
echo ============================================
echo   Шаховий сервер
echo ============================================
cd /d "%~dp0"
echo.
echo  [1] Запустити локально (localhost)
echo  [2] Запустити через ngrok (публічний доступ)
echo.
set /p CHOICE="Вибір (1 або 2): "

if "%CHOICE%"=="2" goto tunnel

:local
echo.
echo  Головне меню:  http://127.0.0.1:8000/ui/menu.html
echo  Натисни Ctrl+C щоб зупинити
echo ============================================
start "" "http://127.0.0.1:8000/ui/menu.html"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
goto end

:tunnel
echo.
echo  Запускаємо сервер на localhost:8000 + ngrok...
echo ============================================
start "Chess Server" cmd /k "cd /d %~dp0 && python -m uvicorn main:app --host 127.0.0.1 --port 8000"
timeout /t 3 /nobreak >nul
echo.
echo  Створюємо ngrok тунель...
ngrok http 8000
goto end

:end
pause
