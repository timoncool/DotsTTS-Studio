@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ========================================
echo   dots.tts Studio - Обновление
echo ========================================

where git >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Git не найден!
    pause
    exit /b 1
)

if exist ".git" (
    echo Обновление портативки...
    git pull
)

if exist "dots.tts\.git" (
    echo Обновление dots.tts...
    cd dots.tts
    git pull
    cd ..
    python\python.exe -m pip install -e "dots.tts" --no-deps -c "dots.tts\constraints\recommended.txt" --no-warn-script-location
    python\python.exe -m pip install -r requirements.txt -c "dots.tts\constraints\recommended.txt" --no-warn-script-location
)

echo Обновление завершено!
pause
