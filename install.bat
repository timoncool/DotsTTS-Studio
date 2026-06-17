@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   dots.tts Studio - Установка
echo ========================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
set "TEMP=%SCRIPT_DIR%temp"
set "TMP=%SCRIPT_DIR%temp"
set "PYTHONUTF8=1"

if not exist "downloads" mkdir downloads
if not exist "temp" mkdir temp
if not exist "models" mkdir models
if not exist "cache" mkdir cache
if not exist "output" mkdir output
if not exist "voices" mkdir voices

REM ============================================================
REM  Шаг 1: GPU. torch 2.8.0; ускорители (triton/flash) НЕ нужны
REM  (dots.tts использует нативный SDPA, optimize=False на Windows).
REM ============================================================
echo.
echo Выберите вариант:
echo.
echo   1. NVIDIA GPU (CUDA 12.8 - RTX 20xx/30xx/40xx/50xx, GTX 10xx)
echo   2. CPU only (без GPU, очень медленно)
echo.
set /p GPU_CHOICE="Введите номер (1-2): "

if "%GPU_CHOICE%"=="1" goto :gpu_nvidia
if "%GPU_CHOICE%"=="2" goto :gpu_cpu
echo Неверный выбор!
pause
exit /b 1

:gpu_nvidia
set "CUDA_VERSION=cu128"
set "CUDA_NAME=NVIDIA CUDA 12.8"
goto :gpu_done
:gpu_cpu
set "CUDA_VERSION=cpu"
set "CUDA_NAME=CPU only"
goto :gpu_done
:gpu_done
echo.
echo Выбрано: %CUDA_NAME%
echo.

REM ============================================================
REM  Шаг 2: Python 3.10.11 embed (pynini-wheel есть только под cp310)
REM ============================================================
if exist "python\python.exe" goto :py_ok
echo [1/8] Скачиваю Python 3.10.11...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip' -OutFile 'downloads\python.zip'}"
powershell -Command "& {Expand-Archive -Path 'downloads\python.zip' -DestinationPath 'python' -Force}"
cd python
if exist "python310._pth" (
    echo python310.zip> python310._pth
    echo .>> python310._pth
    echo Lib\site-packages>> python310._pth
    echo ..\Lib\site-packages>> python310._pth
    echo import site>> python310._pth
)
cd ..
echo [OK] Python 3.10.11 установлен
:py_ok

REM ============================================================
REM  Шаг 3: pip
REM ============================================================
if exist "python\Scripts\pip.exe" goto :pip_ok
echo [2/8] Устанавливаю pip...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'downloads\get-pip.py'}"
python\python.exe downloads\get-pip.py --no-warn-script-location
:pip_ok
python\python.exe -m pip install --upgrade pip setuptools wheel --no-warn-script-location

REM ============================================================
REM  Шаг 4: PyTorch 2.8.0
REM ============================================================
echo [3/8] Устанавливаю PyTorch 2.8.0 (%CUDA_NAME%)...
if "%CUDA_VERSION%"=="cpu" goto :torch_cpu
python\python.exe -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128 --no-warn-script-location
goto :torch_done
:torch_cpu
python\python.exe -m pip install torch==2.8.0 torchaudio==2.8.0 --no-warn-script-location
:torch_done

REM ============================================================
REM  Шаг 5: pynini (prebuilt cp310) + WeTextProcessing.
REM  utils/text.py импортит `tn` на верхнем уровне -> без него
REM  import dots_tts.runtime падает. Даёт нормализацию чисел/дат.
REM ============================================================
echo [4/8] Устанавливаю pynini (prebuilt) + WeTextProcessing...
python\python.exe -m pip install "https://github.com/billwuhao/pynini-windows-wheels/releases/download/v2.1.6.post1/pynini-2.1.6.post1-cp310-cp310-win_amd64.whl" --no-warn-script-location
python\python.exe -m pip install WeTextProcessing --no-deps --no-warn-script-location
python\python.exe -m pip install importlib_resources --no-warn-script-location

REM ============================================================
REM  Шаг 6: dots.tts (клон + editable БЕЗ deps, иначе тянет pynini из исходника)
REM ============================================================
where git >nul 2>&1
if errorlevel 1 goto :no_git
if exist "dots.tts\.git" goto :have_repo
echo [5/8] Клонирую dots.tts...
git clone https://github.com/rednote-hilab/dots.tts dots.tts
:have_repo
echo [6/8] Устанавливаю dots.tts (--no-deps)...
python\python.exe -m pip install -e "dots.tts" --no-deps -c "dots.tts\constraints\recommended.txt" --no-warn-script-location
goto :after_repo
:no_git
echo ОШИБКА: Git не найден! Установите https://git-scm.com/downloads и повторите.
pause
exit /b 1
:after_repo

REM ============================================================
REM  Шаг 7: остальные зависимости
REM ============================================================
echo [7/8] Устанавливаю зависимости...
python\python.exe -m pip install -r requirements.txt -c "dots.tts\constraints\recommended.txt" --no-warn-script-location

echo Устанавливаю ASR Parakeet (onnx-asr, как в shorts-dub)...
python\python.exe -m pip install onnx-asr==0.11.0 sherpa-onnx==1.13.2 --no-warn-script-location
if "%CUDA_VERSION%"=="cpu" goto :ort_cpu
python\python.exe -m pip install onnxruntime-gpu==1.23.2 nvidia-cublas-cu12 nvidia-cudnn-cu12 nvidia-cufft-cu12 nvidia-curand-cu12 nvidia-cusparse-cu12 --no-warn-script-location
goto :ort_done
:ort_cpu
python\python.exe -m pip install onnxruntime --no-warn-script-location
:ort_done

REM ============================================================
REM  Шаг 8: стартовый voice-pack (реф-голоса для клонирования)
REM ============================================================
echo [8/8] Загружаю стартовые голоса...
if exist "voices\*.mp3" goto :voices_ok
curl -L -o downloads\voice-pack.zip https://huggingface.co/datasets/nerualdreming/VibeVoice/resolve/main/voice-pack.zip
if not exist "downloads\voice-pack.zip" goto :voices_ok
powershell -Command "& {Expand-Archive -Path 'downloads\voice-pack.zip' -DestinationPath 'downloads\vp' -Force}"
if exist "downloads\vp\voice-pack" goto :vp_nested
xcopy /E /Y /Q "downloads\vp\*" "voices\" >nul
goto :voices_ok
:vp_nested
xcopy /E /Y /Q "downloads\vp\voice-pack\*" "voices\" >nul
:voices_ok

REM ===== Проверка установки: весь импорт-чейн (torch + pynini/tn + dots.tts) =====
echo Проверка установки...
python\python.exe -c "import torch, dots_tts.runtime; print('[OK] torch', torch.__version__, '| CUDA:', torch.cuda.is_available())"
if errorlevel 1 echo [ВНИМАНИЕ] Проверка импорта не прошла - см. ошибки выше (не хватает зависимости?).

REM ===== Модель по умолчанию (mf, ~5 ГБ) качается ЗДЕСЬ, чтобы первый запуск был без ожидания =====
echo Загружаю модель по умолчанию dots.tts-mf (~5 ГБ)...
set "HF_HOME=%SCRIPT_DIR%models"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
python\python.exe -c "from huggingface_hub import snapshot_download; snapshot_download('rednote-hilab/dots.tts-mf')"
if errorlevel 1 echo [ВНИМАНИЕ] Модель не докачалась - скачается при первом запуске.

echo Загружаю ASR Parakeet (int8 ~670 МБ, для авто-транскрипта и обрезки длинных рефов)...
python\python.exe -c "import onnx_asr; onnx_asr.load_model('nemo-parakeet-tdt-0.6b-v3', quantization='int8')"
if errorlevel 1 echo [ВНИМАНИЕ] Parakeet не докачался - скачается при первом распознавании.

echo %CUDA_VERSION%> cuda_version.txt

echo ========================================
echo   Установка завершена! Запуск: run.bat
echo ========================================
pause
