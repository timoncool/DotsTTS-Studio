<div align="center">

# dots.tts Studio

**Портативная локальная озвучка на [dots.tts](https://github.com/rednote-hilab/dots.tts) (RedNote hilab) — модель без кодек-токенов: выразительная речь на 100+ языках, zero-shot клонирование голоса, живой стриминг, режимы мульти-голос и пакет. 100% офлайн, в один клик.**

[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/timoncool/DotsTTS-Studio?style=flat-square)](https://github.com/timoncool/DotsTTS-Studio/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/timoncool/DotsTTS-Studio?style=flat-square)](https://github.com/timoncool/DotsTTS-Studio/commits/main)

**[English](README.md)** · **[Русский](README_RU.md)**

</div>

dots.tts Studio оборачивает **dots.tts** от RedNote hilab в чистую Windows-портативку в один клик с тёмным RU/EN интерфейсом — намного больше, чем оригинальное демо. Всё живёт внутри папки: Python, зависимости, модели, кэш. Удалил папку — удалил приложение. **100% офлайн**, без облака и API-ключей.

В основе — семейство [dots.tts](https://huggingface.co/rednote-hilab): ~2B полностью непрерывная (без кодек-токенов) авторегрессионная TTS — текстовый бэкбон Qwen2.5-1.5B, flow-matching DiT-голова поверх непрерывных VAE-латентов 48 кГц и CAM++ эмбеддинг говорящего для тембра. Apache-2.0.

## Возможности

- **🎙️ Озвучка** — текст → речь, 100+ языков; **живой стриминг** (играет по мере синтеза); ⏹ Стоп прерывает на лету; авто-чанкинг длинного текста с кроссфейдом.
- **🧬 Клонирование** — zero-shot по референсу: continuation-клон (с транскриптом, лучшее сходство) или только тембр **x-vector** (без транскрипта). Кнопка авто-транскрипта на **мультиязычном Whisper**; библиотека пресетов + докачка **русского пака голосов (700+)**.
- **🎬 Мульти-голос** — ручной сценарий `Speaker N:` → каждый спикер своим голосом, склейка с **выравниванием громкости** (LUFS −16, стандарт подкастов).
- **📦 Пакет** — список текстов → массовый синтез с живым логом.
- **⚙️ Контроль** — выбор модели, тег языка (авто + 12 пресетов), `num_steps`, `guidance`, `speaker_scale`, сид; форматы **WAV / MP3 / FLAC / OGG** (48 кГц) в `output/` с таймстампами. Интерфейс **RU / EN**, тёмная тема.

**Модели (качаются при первом запуске, ~5.2 ГБ каждая):**

| Модель | Что это | Шагов |
|---|---|---|
| **mf** (дефолт) | MeanFlow-дистилл — **быстрее всего** | 4 |
| **soar** | self-corrective-aligned — **лучший клон** | 10 |
| **base** | базовая | 10 |

## Системные требования

- **Windows 10/11**, **NVIDIA GPU** (RTX 20xx–50xx, **~8 ГБ VRAM**). CPU работает, но очень медленно.
- **~13 ГБ диска** (PyTorch + одна модель). Модели качаются автоматически при первом запуске.
- Ускорение: bf16 + flash-ядра PyTorch SDPA (flash-attn/triton не нужны). Самый быстрый синтез — модель `mf`.

## Установка

1. **Скачайте** этот репозиторий (Code → Download ZIP или `git clone`).
2. **Установка** — запустите **`install.bat`**, выберите GPU (`1` = NVIDIA / `2` = CPU). Поставит портативный Python 3.10, PyTorch 2.8 (CUDA 12.8) и все зависимости.
3. **Запуск** — запустите **`run.bat`**; приложение откроется в браузере, модель скачается при первом старте. Обновление — **`update.bat`**.

> Для лучшего клона: дайте **~10 с чистого референса**, заполните транскрипт (или нажмите **Распознать**) и выставьте язык явно.

## Другие портативные нейросети от [timoncool](https://github.com/timoncool)

| Проект | Описание |
|--------|----------|
| [Higgs Audio Studio](https://github.com/timoncool/HiggsAudio-Studio) | Выразительная TTS + AI-режиссёр, подкаст и аудиокнига |
| [VoxCPM2 Portable](https://github.com/timoncool/VoxCPM2_portable) | Мультиязычная TTS + Voice Design + LoRA-обучение |
| [Qwen3-TTS](https://github.com/timoncool/Qwen3-TTS_portable_rus) | Портативная озвучка с клонированием голоса |
| [ACE-Step Studio](https://github.com/timoncool/ACE-Step-Studio) | AI-музстудия — песни, вокал, каверы, видео |
| [Foundation Music Lab](https://github.com/timoncool/Foundation-Music-Lab) | Генерация музыки + таймлайн-редактор |
| [VibeVoice ASR](https://github.com/timoncool/VibeVoice_ASR_portable_ru) | Портативное распознавание речи |
| [LavaSR](https://github.com/timoncool/LavaSR_portable_ru) | Портативное улучшение качества аудио |
| [VideoSOS](https://github.com/timoncool/videosos) | AI-видеопродакшн в браузере |

## Авторы

- **Nerual Dreming** — [Telegram](https://t.me/nerual_dreming) | [neuro-cartel.com](https://neuro-cartel.com) | [ArtGeneration.me](https://artgeneration.me)
- **Нейро-Софт** — [Telegram](https://t.me/neuroport) | портативки нейросетей

## Благодарности

- **[dots.tts](https://github.com/rednote-hilab/dots.tts)** от RedNote hilab — TTS-модель (Apache-2.0)
- **[Whisper](https://huggingface.co/openai/whisper-base)** — мультиязычное распознавание референса
- **[Slait/russia_voices](https://huggingface.co/datasets/Slait/russia_voices)** — русские пресеты голосов
- **[pyloudnorm](https://github.com/csteinmetz1/pyloudnorm)** — выравнивание громкости EBU R128 · **[Gradio](https://gradio.app/)** — UI

## Лицензия

**Apache-2.0** (обёртка и dots.tts). Клонирование голоса — только с согласия владельца; имперсонация, мошенничество и любое незаконное использование запрещены.
