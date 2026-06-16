@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   dots.tts Studio
echo ========================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if not exist "python\python.exe" (
    echo ОШИБКА: Python не найден! Запустите install.bat
    pause
    exit /b 1
)
if not exist "app.py" (
    echo ОШИБКА: app.py не найден!
    pause
    exit /b 1
)

if exist "cuda_version.txt" (
    set /p CUDA_VERSION=<cuda_version.txt
    echo Конфигурация: !CUDA_VERSION!
)

REM === Изоляция: все кэши/модели/temp ВНУТРИ папки приложения ===
set "TEMP=%SCRIPT_DIR%temp"
set "TMP=%SCRIPT_DIR%temp"
set "GRADIO_TEMP_DIR=%SCRIPT_DIR%temp"
if not exist "%TEMP%" mkdir "%TEMP%"

set "HF_HOME=%SCRIPT_DIR%models"
set "HUGGINGFACE_HUB_CACHE=%SCRIPT_DIR%models"
set "TRANSFORMERS_CACHE=%SCRIPT_DIR%models"
if not exist "%HF_HOME%" mkdir "%HF_HOME%"

set "TORCH_HOME=%SCRIPT_DIR%models\torch"
if not exist "%TORCH_HOME%" mkdir "%TORCH_HOME%"

set "XDG_CACHE_HOME=%SCRIPT_DIR%cache"
if not exist "%XDG_CACHE_HOME%" mkdir "%XDG_CACHE_HOME%"

REM === Windows-фиксы dots.tts ===
REM StaticCudaLauncher падает на torch 2.8 (pytorch#162430); символlink-копии HF на Windows; UTF-8.
set "TORCHINDUCTOR_USE_STATIC_CUDA_LAUNCHER=0"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUNBUFFERED=1"

if exist "%SCRIPT_DIR%ffmpeg\ffmpeg.exe" set "PATH=%SCRIPT_DIR%ffmpeg;%PATH%"

echo Запуск приложения...
python\python.exe app.py

if errorlevel 1 (
    echo.
    echo ОШИБКА при запуске! Возможные причины:
    echo  1. Не установлены зависимости - запустите install.bat
    echo  2. Недостаточно VRAM (нужно ~8 ГБ)
    echo  3. Старый CUDA-драйвер (для CUDA 12.8 нужен свежий драйвер NVIDIA)
    pause
    exit /b 1
)
pause
