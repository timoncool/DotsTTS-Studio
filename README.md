<div align="center">

# dots.tts Studio

**Portable local text-to-speech built on [dots.tts](https://github.com/rednote-hilab/dots.tts) (RedNote hilab) — a codec-token-free model: expressive speech in 100+ languages, zero-shot voice cloning, live streaming playback, plus multi-voice and batch modes. 100% offline, one click.**

[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/timoncool/DotsTTS-Studio?style=flat-square)](https://github.com/timoncool/DotsTTS-Studio/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/timoncool/DotsTTS-Studio?style=flat-square)](https://github.com/timoncool/DotsTTS-Studio/commits/main)

**[English](README.md)** · **[Русский](README_RU.md)**

</div>

dots.tts Studio wraps **dots.tts** by RedNote hilab in a clean Windows one-click portable with a Russian/English dark UI — far beyond the upstream demo. Everything lives inside the folder: Python, dependencies, models, cache. Delete the folder — the app is gone. **100% offline**, no cloud, no API keys.

Built on the [dots.tts](https://huggingface.co/rednote-hilab) family — a ~2B fully-continuous (no codec tokens) autoregressive TTS: a Qwen2.5-1.5B text backbone, a flow-matching DiT head over continuous 48 kHz VAE latents, and a CAM++ speaker embedding for timbre. Apache-2.0.

## Features

- **🎙️ TTS** — text → speech, 100+ languages; **live streaming playback** (audio plays as it generates); ⏹ Stop interrupts mid-stream; auto-chunking of long text with crossfade.
- **🧬 Voice cloning** — zero-shot from a reference clip: continuation clone (with transcript, best similarity) or timbre-only **x-vector** (no transcript). **Multilingual Whisper** auto-transcription button; preset library + on-demand **Russian voice pack (700+)**.
- **🎬 Multi-voice** — a manual `Speaker N:` script → each speaker its own voice, stitched with **loudness leveling across speakers** (LUFS −16, podcast standard).
- **📦 Batch** — a list of texts → mass synthesis with a live log.
- **⚙️ Control** — model picker, language tag (auto-detect + 12 presets), `num_steps`, `guidance`, `speaker_scale`, seed; output **WAV / MP3 / FLAC / OGG** (48 kHz) saved to `output/` with timestamps. **RU / EN** UI, dark theme.

**Models (download on first run, ~5.2 GB each):**

| Model | What it is | Steps |
|---|---|---|
| **mf** (default) | MeanFlow-distilled — **fastest** | 4 |
| **soar** | self-corrective-aligned — **best cloning** | 10 |
| **base** | pretrained foundation | 10 |

## System Requirements

- **Windows 10/11**, **NVIDIA GPU** (RTX 20xx–50xx, **~8 GB VRAM**). CPU works but is very slow.
- **~13 GB disk** (PyTorch + one model). Models download automatically on first launch.
- Acceleration: bf16 + PyTorch SDPA flash kernels (no flash-attn/triton needed). Use the `mf` model for the fastest generation.

## Quick Start

1. **Download** this repository (Code → Download ZIP, or `git clone`).
2. **Install** — run **`install.bat`**, pick your GPU (`1` = NVIDIA / `2` = CPU). It sets up portable Python 3.10, PyTorch 2.8 (CUDA 12.8) and all dependencies.
3. **Run** — run **`run.bat`**; the app opens in the browser, the model downloads on first launch. Update with **`update.bat`**.

> Tip for best cloning: give a **~10 s clean reference**, fill the transcript (or press **Transcribe**), and set the language explicitly.

## Other Projects by [timoncool](https://github.com/timoncool)

| Project | Description |
|---------|-------------|
| [Higgs Audio Studio](https://github.com/timoncool/HiggsAudio-Studio) | Expressive TTS + AI director, podcast & audiobook |
| [VoxCPM2 Portable](https://github.com/timoncool/VoxCPM2_portable) | Multilingual TTS + Voice Design + LoRA fine-tuning |
| [Qwen3-TTS](https://github.com/timoncool/Qwen3-TTS_portable_rus) | Portable text-to-speech with voice cloning |
| [ACE-Step Studio](https://github.com/timoncool/ACE-Step-Studio) | AI music studio — songs, vocals, covers, videos |
| [Foundation Music Lab](https://github.com/timoncool/Foundation-Music-Lab) | Music generation + timeline editor |
| [VibeVoice ASR](https://github.com/timoncool/VibeVoice_ASR_portable_ru) | Portable speech recognition |
| [LavaSR](https://github.com/timoncool/LavaSR_portable_ru) | Portable audio enhancement |
| [VideoSOS](https://github.com/timoncool/videosos) | AI video production in the browser |

## Authors

- **Nerual Dreming** — [Telegram](https://t.me/nerual_dreming) | [neuro-cartel.com](https://neuro-cartel.com) | [ArtGeneration.me](https://artgeneration.me)
- **Нейро-Софт** — [Telegram](https://t.me/neuroport) | portable AI builds

## Acknowledgments

- **[dots.tts](https://github.com/rednote-hilab/dots.tts)** by RedNote hilab — the TTS model (Apache-2.0)
- **[Whisper](https://huggingface.co/openai/whisper-base)** — multilingual reference transcription
- **[Slait/russia_voices](https://huggingface.co/datasets/Slait/russia_voices)** — Russian voice presets
- **[pyloudnorm](https://github.com/csteinmetz1/pyloudnorm)** — EBU R128 loudness leveling · **[Gradio](https://gradio.app/)** — UI framework

## Star History

<a href="https://www.star-history.com/?repos=timoncool%2FDotsTTS-Studio&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=timoncool/DotsTTS-Studio&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=timoncool/DotsTTS-Studio&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=timoncool/DotsTTS-Studio&type=date&legend=top-left" />
 </picture>
</a>

## License

**Apache-2.0** (this wrapper and dots.tts). Voice cloning only with the consent of the voice owner; impersonation, fraud and any illegal use are prohibited.
