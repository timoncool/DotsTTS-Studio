"""Движок dots.tts (rednote-hilab) — обёртка над штатным DotsTtsRuntime.

- Загрузка soar/mf/base, авто-bf16, optimize=False (Windows: torch.compile падает).
- Озвучка/клон: живой стрим (generate_stream); пакет/мульти: быстрый generate() (вокодер 1 раз).
- Длинная форма: чанкинг ≤200 симв, сид 1 раз на запрос, кроссфейд (гасит скачок тембра).
- Мульти-голос: LUFS-выравнивание спикеров (переиспользовано из Higgs Audio Studio).
- Тяжёлые импорты ленивые (внутри функций) — mock-режим и UI поднимаются без torch.
"""
import os

DOTS_MOCK = bool(os.environ.get("DOTS_UI_MOCK"))
SR_FALLBACK = 48000

# label -> HF repo id. mf = 4 шага (быстро, дефолт), soar = лучший клон, base = база.
MODELS = {
    "mf · быстро, 4 шага · ~5.2 ГБ (дефолт)": "rednote-hilab/dots.tts-mf",
    "soar · лучший клон, макс. качество · ~5.2 ГБ": "rednote-hilab/dots.tts-soar",
    "base · база · ~5.2 ГБ": "rednote-hilab/dots.tts-base",
}
DEFAULT_MODEL = "mf · быстро, 4 шага · ~5.2 ГБ (дефолт)"

CHUNK_MAX_CHARS = 200   # наша эвристика: дробим для стабильности длинной формы и кроссфейда
REF_MAX_SEC = 90        # режем ТОЛЬКО экстремально длинный реф. Обрезка рвёт транскрипт→x-vector→глюк,
                        # поэтому держим высоко: пресеты ≤~55с идут полным continuation-клоном (чисто)

_runtime = None
_loaded = None          # (repo_id, precision) что сейчас в памяти
_forced_precision = "bfloat16"


def is_mf(label):
    return "-mf" in model_repo(label)


# ----------------------------------------------------------------------------
# Устройство / точность
# ----------------------------------------------------------------------------
def detect_device():
    import torch
    if torch.cuda.is_available():
        p = torch.cuda.get_device_properties(0)
        return "cuda", p.name, p.total_memory / 1e9
    return "cpu", "CPU", 0.0


def device_info():
    if DOTS_MOCK:
        return "MOCK UI (без модели)"
    try:
        dev, name, vram = detect_device()
    except Exception:
        return "CPU"
    return f"{name} | VRAM {vram:.1f} ГБ" if dev == "cuda" else "CPU (медленно)"


def set_precision(p):
    """UI: 'bfloat16' / 'float16' / 'float32'. Выгружает модель — перезагрузится в новой точности."""
    global _forced_precision
    _forced_precision = p if p in ("bfloat16", "float16", "float32") else "bfloat16"
    unload()


def model_repo(label):
    return MODELS.get(label, MODELS[DEFAULT_MODEL])


# ----------------------------------------------------------------------------
# Загрузка / выгрузка рантайма
# ----------------------------------------------------------------------------
def get_runtime(label=DEFAULT_MODEL, precision=None):
    global _runtime, _loaded
    if DOTS_MOCK:
        return "MOCK"
    repo = model_repo(label)
    precision = precision or _forced_precision
    if _runtime is not None and _loaded == (repo, precision):
        return _runtime
    unload()
    from dots_tts.runtime import DotsTtsRuntime
    print(f"[dots] загрузка {repo} ({precision}, optimize=False)...", flush=True)
    # max_generate_length с запасом: реф ≤15с + длинная генерация укладываются
    # (рантайм режет schedule prompt+generated по этому кэпу).
    _runtime = DotsTtsRuntime.from_pretrained(
        repo, precision=precision, optimize=False, max_generate_length=4000)
    _loaded = (repo, precision)
    print(f"[dots] готово: {repo} @ {_runtime.sample_rate} Гц", flush=True)
    return _runtime


def unload():
    global _runtime, _loaded
    _runtime = None
    _loaded = None
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


# ----------------------------------------------------------------------------
# Отмена генерации
# ----------------------------------------------------------------------------
_CANCEL = False


def request_cancel():
    global _CANCEL
    _CANCEL = True
    print("[gen] STOP — прерываю генерацию", flush=True)


def clear_cancel():
    global _CANCEL
    _CANCEL = False


def cancelled():
    return _CANCEL


def _seed(seed):
    try:
        from dots_tts.utils.util import seed_everything
        seed_everything(int(seed))
    except Exception as e:
        print(f"[gen] seed: {e}", flush=True)


# ----------------------------------------------------------------------------
# Аудио-хелперы (LUFS/склейка/тримминг) — из Higgs Audio Studio
# ----------------------------------------------------------------------------
TARGET_LUFS = -16.0
_PEAK_CEIL = 10 ** (-1.0 / 20)
_MAX_GAIN = 10 ** (20.0 / 20)


def _loudness_normalize(x, sr):
    import numpy as np
    x = np.asarray(x, dtype=np.float32)
    if x.size == 0:
        return x
    try:
        import pyloudnorm as pyln
        loud = pyln.Meter(sr).integrated_loudness(x)
        if np.isfinite(loud):
            return (x * min(10 ** ((TARGET_LUFS - loud) / 20), _MAX_GAIN)).astype(np.float32)
    except Exception:
        pass
    rms = float(np.sqrt(np.mean(x ** 2)))
    if rms < 1e-6:
        return x
    return (x * min((10 ** (-20.0 / 20)) / rms, _MAX_GAIN)).astype(np.float32)


def _peak_limit(x, ceil=_PEAK_CEIL):
    import numpy as np
    if x.size == 0:
        return x
    peak = float(np.max(np.abs(x)))
    return (x * (ceil / peak)).astype(np.float32) if peak > ceil else x


def _trim_tail(x, sr, top_db=38):
    """Срезать хвостовую тишину (band-aid против EOS-мусора на коротком тексте)."""
    import numpy as np
    try:
        import librosa
        idx = librosa.effects.split(x, top_db=top_db)
        if len(idx):
            return x[: int(idx[-1][1])].astype(np.float32)
    except Exception:
        pass
    return np.asarray(x, dtype=np.float32)


def _concat_xfade(chunks, sr, fade=0.08):
    """Склейка кусков ОДНОГО голоса с кроссфейдом — гасит скачок тембра между чанками."""
    import numpy as np
    chunks = [np.asarray(c, np.float32) for c in chunks if c is not None and len(c)]
    if not chunks:
        return np.zeros(0, np.float32)
    n = max(1, int(sr * fade))
    out = chunks[0]
    for c in chunks[1:]:
        if len(out) >= n and len(c) >= n:
            ramp = np.linspace(0, 1, n, dtype=np.float32)
            head = out[:-n]
            mix = out[-n:] * (1 - ramp) + c[:n] * ramp
            out = np.concatenate([head, mix, c[n:]])
        else:
            out = np.concatenate([out, c])
    return out.astype(np.float32)


def _concat_gap(chunks, sr, gap=0.3, normalize=True):
    """Склейка РАЗНЫХ голосов с паузой + LUFS-выравниванием (один спикер не тише другого)."""
    import numpy as np
    chunks = [c for c in chunks if c is not None and len(c)]
    if not chunks:
        return np.zeros(0, np.float32)
    if normalize:
        chunks = [_loudness_normalize(c, sr) for c in chunks]
    sil = np.zeros(int(sr * gap), np.float32)
    out = []
    for i, c in enumerate(chunks):
        if i:
            out.append(sil)
        out.append(c)
    mix = np.concatenate(out)
    return _peak_limit(mix) if normalize else mix


def _chunk(text, max_chars=CHUNK_MAX_CHARS):
    import re
    text = (text or "").strip()
    if not text:
        return []
    chunks = []
    for para in (p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()):
        if len(para) <= max_chars:
            chunks.append(para)
            continue
        cur = ""
        for s in re.split(r"(?<=[.!?…。！？])\s+", para):
            if cur and len(cur) + len(s) > max_chars:
                chunks.append(cur.strip())
                cur = s
            else:
                cur = (cur + " " + s).strip()
        if cur:
            chunks.append(cur)
    return chunks


# ----------------------------------------------------------------------------
# Референс: обрезка длинного клипа во временный wav (ограничить prefill)
# ----------------------------------------------------------------------------
def _prep_ref(path):
    """Реф → (путь, обрезан?). Если длиннее REF_MAX_SEC — обрезанная temp-копия (caller её удалит).
    Флаг 'обрезан' нужен, чтобы НЕ слать транскрипт полного аудио к обрезанному (рассинхрон → разнос)."""
    if not path:
        return None, False
    try:
        import soundfile as sf
        info = sf.info(path)
        if info.frames / max(info.samplerate, 1) <= REF_MAX_SEC:
            return path, False
        import tempfile
        import numpy as np
        data, sr = sf.read(path, dtype="float32", always_2d=True)
        data = data[: int(sr * REF_MAX_SEC)].mean(axis=1)
        f = tempfile.NamedTemporaryFile(suffix="._dotsref.wav", delete=False, dir=os.environ.get("TEMP"))
        f.close()
        sf.write(f.name, data.astype(np.float32), sr)
        print(f"[gen] референс обрезан до {REF_MAX_SEC}с → транскрипт отключён (x-vector)", flush=True)
        return f.name, True
    except Exception as e:
        print(f"[gen] ref prep: {e}", flush=True)
        return path, False


def _cleanup_ref(prepared, original):
    """Удалить temp-реф, если _prep_ref его создавал."""
    if prepared and prepared != original:
        try:
            os.remove(prepared)
        except OSError:
            pass


def _script_lang(text):
    """Доминирующий скрипт текста → языковой код dots.tts. Авто-детект модели знает только zh/en,
    поэтому кириллицу/кану/арабицу и пр. подставляем сами, иначе модель лепит кашу."""
    import unicodedata
    c = {}
    for ch in text or "":
        if not ch.isalpha():
            continue
        try:
            nm = unicodedata.name(ch)
        except ValueError:
            continue
        if "CYRILLIC" in nm:
            k = "RU"
        elif "HANGUL" in nm:
            k = "KO"
        elif "HIRAGANA" in nm or "KATAKANA" in nm:
            k = "JA"
        elif "CJK" in nm:
            k = "ZH"
        elif "ARABIC" in nm:
            k = "AR"
        elif "HEBREW" in nm:
            k = "HE"
        elif "DEVANAGARI" in nm:
            k = "HI"
        elif "GREEK" in nm:
            k = "EL"
        else:
            continue   # латиница и пр. → пусть dots.tts сам детектит (en)
        c[k] = c.get(k, 0) + 1
    return max(c, key=c.get) if c else None


def _lang(language, text=""):
    s = str(language or "").strip()
    low = s.lower()
    if low in ("", "none", "—", "авто", "auto"):
        return None
    if low == "auto_detect":
        return _script_lang(text) or "auto_detect"   # кириллица→RU, кана→JA…; латиница→dots.tts(en)
    return s


def _prep_call(label, ref_audio, ref_text, num_steps):
    """Общая подготовка вызова: рантайм, шаги (mf=4), реф (обрезка), транскрипт.
    x-vector = аудио без транскрипта; continuation-клон = аудио + транскрипт."""
    rt = get_runtime(label)
    steps = 4 if is_mf(label) else int(num_steps)
    if not ref_audio:
        return rt, steps, None, None
    if ref_text and ref_text.strip():
        # continuation-клон: транскрипт ОБЯЗАН совпадать с аудио (доки) → НЕ режем реф вообще.
        # Рантайм кэширует кондишн рефа, так что повторное использование голоса дёшево.
        return rt, steps, ref_audio, ref_text.strip()
    # x-vector (только тембр, транскрипта нет → мисматчить нечего) → длинный реф можно подрезать
    pa, _ = _prep_ref(ref_audio)
    return rt, steps, pa, None


# ----------------------------------------------------------------------------
# Генерация
# ----------------------------------------------------------------------------
def generate_one(text, *, label=DEFAULT_MODEL, ref_audio=None, ref_text=None, language=None,
                 num_steps=10, guidance_scale=1.2, speaker_scale=1.5, normalize=False, seed=-1):
    """Один фрагмент через generate() — вокодер 1 раз в конце (быстрее stream).
    Для не-стрим вкладок (Пакет/Мульти). Возвращает (sr, np.float32[L])."""
    import numpy as np
    text = (text or "").strip()
    if not text:
        return SR_FALLBACK, np.zeros(0, np.float32)
    if DOTS_MOCK:
        n = int(SR_FALLBACK * 1.2)
        return SR_FALLBACK, (0.2 * np.sin(2 * np.pi * 220 * np.arange(n) / SR_FALLBACK)).astype(np.float32)
    if seed is not None and int(seed) >= 0:
        _seed(seed)
    rt, steps, pa, pt = _prep_call(label, ref_audio, ref_text, num_steps)
    try:
        r = rt.generate(text=text, prompt_audio_path=pa, prompt_text=pt, language=_lang(language, text),
                        speaker_scale=float(speaker_scale), num_steps=steps,
                        guidance_scale=float(guidance_scale), normalize_text=bool(normalize))
    finally:
        _cleanup_ref(pa, ref_audio)
    sr = r["sample_rate"]
    audio = r["audio"].detach().float().cpu().numpy().reshape(-1)
    print(f"[gen] {len(audio) / sr:.1f}с · RTF {r.get('rtf', 0):.2f}", flush=True)
    return sr, _trim_tail(audio, sr)


def synth_text(text, *, label=DEFAULT_MODEL, ref_audio=None, ref_text=None, language=None,
               num_steps=10, guidance_scale=1.2, speaker_scale=1.5, normalize=False, seed=-1):
    """Текст любой длины: короткий — одним проходом, длинный — чанки ≤200 + кроссфейд.
    Итог нормализуется (LUFS −16 + пик-лимит −1 dBFS) — ровный уровень, без горячего звука/клиппинга."""
    import numpy as np
    chunks = _chunk(text)
    if len(chunks) <= 1:
        sr, wav = generate_one(text, label=label, ref_audio=ref_audio, ref_text=ref_text,
                               language=language, num_steps=num_steps, guidance_scale=guidance_scale,
                               speaker_scale=speaker_scale, normalize=normalize, seed=seed)
    else:
        if seed is not None and int(seed) >= 0:
            _seed(seed)   # сид 1 раз на весь текст; чанки наследуют продолжение RNG
        sr, parts = SR_FALLBACK, []
        for i, ch in enumerate(chunks):
            if _CANCEL:
                break
            print(f"[gen] чанк {i + 1}/{len(chunks)}", flush=True)
            sr, a = generate_one(ch, label=label, ref_audio=ref_audio, ref_text=ref_text,
                                 language=language, num_steps=num_steps, guidance_scale=guidance_scale,
                                 speaker_scale=speaker_scale, normalize=normalize, seed=-1)
            if len(a):
                parts.append(a)
        wav = _concat_xfade(parts, sr)
    if not len(wav):
        return sr, np.asarray(wav, np.float32)
    return sr, _peak_limit(_loudness_normalize(wav, sr))


def synth_text_stream(text, *, label=DEFAULT_MODEL, ref_audio=None, ref_text=None, language=None,
                      num_steps=10, guidance_scale=1.2, speaker_scale=1.5, normalize=False, seed=-1,
                      buffer_sec=0.4):
    """Генератор ЖИВОГО стрима: yield (sr, chunk_np) по мере синтеза → проигрывается на лету.
    Буферизует ~buffer_sec (плавность), хвост последнего буфера триммится (EOS-мусор не слышен)."""
    import numpy as np
    text = (text or "").strip()
    if not text:
        return
    if DOTS_MOCK:
        for _ in range(4):
            yield SR_FALLBACK, (0.2 * np.sin(2 * np.pi * 220 * np.arange(int(SR_FALLBACK * 0.3)) / SR_FALLBACK)).astype(np.float32)
        return
    if seed is not None and int(seed) >= 0:
        _seed(seed)
    rt, steps, pa, pt = _prep_call(label, ref_audio, ref_text, num_steps)
    sr = rt.sample_rate
    target = max(1, int(sr * buffer_sec))
    buf, buf_len = [], 0
    try:
        for ch in (_chunk(text) or [text]):
            if _CANCEL:
                break
            for chunk in rt.generate_stream(text=ch, prompt_audio_path=pa, prompt_text=pt,
                                            language=_lang(language, ch), speaker_scale=float(speaker_scale),
                                            num_steps=steps, guidance_scale=float(guidance_scale),
                                            normalize_text=bool(normalize)):
                if _CANCEL:
                    break
                c = chunk.detach().float().cpu().numpy().reshape(-1)
                buf.append(c)
                buf_len += len(c)
                if buf_len >= target:
                    yield sr, np.concatenate(buf).astype(np.float32)
                    buf, buf_len = [], 0
            # конец текст-чанка: остаток с тримом хвоста (убирает EOS-мусор на стыке чанков)
            if buf:
                yield sr, _trim_tail(np.concatenate(buf).astype(np.float32), sr)
                buf, buf_len = [], 0
        if buf:
            yield sr, _trim_tail(np.concatenate(buf).astype(np.float32), sr)
    finally:
        _cleanup_ref(pa, ref_audio)


def synth_turns(turns, *, label=DEFAULT_MODEL, gap=0.3, seed=-1, on_progress=None, **kw):
    """turns: [{'text','ref_audio','ref_text'}] — каждый спикер своим голосом, LUFS-склейка."""
    if seed is not None and int(seed) >= 0:
        _seed(seed)
    sr, parts = SR_FALLBACK, []
    n = len(turns)
    for i, t in enumerate(turns):
        if _CANCEL:
            break
        if on_progress:
            on_progress(i, n)
        if (t.get("text") or "").strip():
            sr, a = synth_text(t["text"], label=label, ref_audio=t.get("ref_audio"),
                              ref_text=t.get("ref_text"), seed=-1, **kw)
            if len(a):
                parts.append(a)
    # турны уже нормализованы в synth_text → склеиваем с паузой без повторной нормализации
    return sr, _concat_gap(parts, sr, gap=gap, normalize=False)
