"""dots.tts Studio — портативная сборка Nerual Dreming + Нейро-Софт.

dots.tts v3 (rednote-hilab): кодек-token-free TTS, 100+ языков, zero-shot клон.
Вкладки: Озвучка · Клонирование · Мульти-голос · Пакет. UI RU/EN, тёмная тема.
БЕЗ LLM — у dots.tts нет тег-системы, эмоции модель берёт из контекста сама.
"""
import os
import re
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Windows retry_open патч для anyio/aiofiles (PermissionError от антивируса)
if sys.platform == "win32":
    try:
        import anyio
        import anyio._core._fileio
        _orig_open = anyio._core._fileio.open_file

        async def _retry_open(file, *a, **k):
            delay = 0.2
            for i in range(20):
                try:
                    return await _orig_open(file, *a, **k)
                except PermissionError:
                    if i == 19:
                        raise
                    await asyncio.sleep(delay)
                    delay *= 1.2

        anyio._core._fileio.open_file = _retry_open
        anyio.open_file = _retry_open
    except Exception:
        pass

from datetime import datetime
from pathlib import Path

import gradio as gr
import numpy as np

import dots_engine as eng

SCRIPT_DIR = Path(__file__).parent.absolute()
OUTPUT_DIR = SCRIPT_DIR / "output"
VOICES_DIR = SCRIPT_DIR / "voices"
OUTPUT_DIR.mkdir(exist_ok=True)
VOICES_DIR.mkdir(exist_ok=True)
REF_CACHE_DIR = SCRIPT_DIR / "cache" / "refcache"   # обрезанный реф + транскрипт (переживает рестарт)
REF_CACHE_DIR.mkdir(parents=True, exist_ok=True)

APP_NAME = "dots.tts Studio"
DEVICE_INFO = eng.device_info()
MODEL_CHOICES = list(eng.MODELS.keys())
MAX_SPK = 4
OWN_FILE = "— свой файл / own file —"
_DEF_VOICE = "RU_Male_Gabidullin_ruslan"   # дефолт-голос Озвучки (русский; модель клонирующая — без рефа щелчки)

CLOUD_VOICES_REPO = "Slait/russia_voices"
CLOUD_VOICES_BASE = "https://huggingface.co/datasets/Slait/russia_voices/resolve/main"

# Язык: значения должны проходить normalize_language_code (langcodes) или быть none/auto_detect.
LANG_CHOICES = [
    ("Авто (по тексту) / Auto", "auto_detect"), ("Без тега / None", "none"),
    ("English", "EN"), ("Русский", "RU"), ("中文", "ZH"), ("日本語", "JA"),
    ("한국어", "KO"), ("Español", "ES"), ("Français", "FR"), ("Deutsch", "DE"),
    ("Italiano", "IT"), ("Português", "PT"), ("العربية", "AR"), ("हिन्दी", "HI"),
]

# ----------------------------------------------------------------------------
# Брендинг (из Higgs Audio Studio)
# ----------------------------------------------------------------------------
_FLAG = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg"

_DONATE_RU = """
<div class="donate-popover">
  <p class="donate-intro">Привет! Я Илья (<a href="https://t.me/nerual_dreming" target="_blank">Nerual Dreming</a>), я создаю AI-инструменты, которые работают локально — бесплатно, без облака, без подписок. Ваш донат позволяет фокусироваться на новых открытых проектах. Спасибо!</p>
  <div class="donate-sep"></div>
  <div class="donate-row"><a href="https://dalink.to/nerual_dreming" target="_blank">💳 Карта / PayPal (рубли, доллары, евро)</a></div>
  <div class="donate-row"><a href="https://boosty.to/neuro_art" target="_blank">🚀 Ежемесячная подписка на Boosty</a></div>
  <div class="donate-sep"></div>
  <div class="donate-row"><span>BTC</span><code>1E7dHL22RpyhJGVpcvKdbyZgksSYkYeEBC</code></div>
  <div class="donate-row"><span>ETH</span><code>0xb5db65adf478983186d4897ba92fe2c25c594a0c</code></div>
  <div class="donate-row"><span>USDT TRC20</span><code>TQST9Lp2TjK6FiVkn4fwfGUee7NmkxEE7C</code></div>
</div>
"""
_DONATE_EN = """
<div class="donate-popover">
  <p class="donate-intro">Hi! I'm Ilya (<a href="https://t.me/nerual_dreming" target="_blank">Nerual Dreming</a>), I build AI tools that run locally — free, no cloud, no subscriptions. Your donation lets me focus on new open-source projects. Thank you!</p>
  <div class="donate-sep"></div>
  <div class="donate-row"><a href="https://dalink.to/nerual_dreming" target="_blank">💳 Card / PayPal (USD, EUR, RUB)</a></div>
  <div class="donate-row"><a href="https://boosty.to/neuro_art" target="_blank">🚀 Monthly subscription on Boosty</a></div>
  <div class="donate-sep"></div>
  <div class="donate-row"><span>BTC</span><code>1E7dHL22RpyhJGVpcvKdbyZgksSYkYeEBC</code></div>
  <div class="donate-row"><span>ETH</span><code>0xb5db65adf478983186d4897ba92fe2c25c594a0c</code></div>
  <div class="donate-row"><span>USDT TRC20</span><code>TQST9Lp2TjK6FiVkn4fwfGUee7NmkxEE7C</code></div>
</div>
"""


def _brand(subtitle, credits, donate, donate_label):
    return f"""
<div class="brand-header">
  <div class="lang-switcher">
    <a href="?__lang=ru&amp;__theme=dark" class="lang-btn"><img src="{_FLAG}/1f1f7-1f1fa.svg" width="16" height="16"/>RU</a>
    <a href="?__lang=en&amp;__theme=dark" class="lang-btn"><img src="{_FLAG}/1f1ec-1f1e7.svg" width="16" height="16"/>EN</a>
    <details class="donate-wrap"><summary class="lang-btn donate-btn"><img src="{_FLAG}/1fa99.svg" width="16" height="16"/>{donate_label}</summary>{donate}</details>
  </div>
  <div class="brand-box">
    <div class="brand-title">🎙️ {APP_NAME}</div>
    <div class="brand-subtitle">{subtitle}</div>
    <div class="brand-credits">{credits}</div>
    <div class="device-badge">💻 {DEVICE_INFO}</div>
  </div>
</div>
"""


BRAND_HTML_RU = _brand(
    "dots.tts · 100+ языков · zero-shot клонирование · подкаст и аудиокнига · 100% локально",
    'Собрал <a href="https://t.me/nerual_dreming" target="_blank">Nerual Dreming</a> — '
    'основатель <a href="https://artgeneration.me" target="_blank">ArtGeneration.me</a>. Канал '
    '<a href="https://t.me/neuroport" target="_blank">Нейро-Софт</a> — репаки и портативки нейросетей.',
    _DONATE_RU, "Донат",
)
BRAND_HTML_EN = _brand(
    "dots.tts · 100+ languages · zero-shot voice cloning · podcast & audiobook · 100% local",
    'Built by <a href="https://t.me/nerual_dreming" target="_blank">Nerual Dreming</a> — '
    'founder of <a href="https://artgeneration.me" target="_blank">ArtGeneration.me</a>. Channel '
    '<a href="https://t.me/neuroport" target="_blank">Нейро-Софт</a> — portable AI builds.',
    _DONATE_EN, "Donate",
)

# ----------------------------------------------------------------------------
# i18n
# ----------------------------------------------------------------------------
_RU = {
    "tab_tts": "🎙️ Озвучка", "tab_clone": "🧬 Клонирование",
    "tab_multi": "🎬 Мульти-голос", "tab_batch": "📦 Пакет",
    "text": "Текст", "ph_text": "Введите текст для озвучки…",
    "tts_voice": "Голос (реф — без него щелчки)",
    "generate": "🔊 Озвучить", "stop": "⏹ Стоп", "result": "Результат", "advanced": "Доп. настройки",
    "model": "Модель", "precision": "Точность (VRAM)", "out_format": "Формат вывода", "language": "Язык",
    "steps": "Шагов (mf = 4)", "guidance": "Guidance (CFG, >2 искажает)",
    "speaker_scale": "Сила тембра референса", "seed": "Сид (-1 = случайно)",
    "normalize": "Нормализовать числа/даты (медленнее)",
    "guid_info": "Только soar/base; у mf CFG встроен (слайдер не влияет).",
    "spk_info": ">1.5 — ближе к референсу, но риск артефактов.",
    "ref_voice": "Аудио-референс (голос)", "ref_text": "Транскрипт референса (для лучшего клона)",
    "ph_ref_text": "Что произносится в референсе… пусто = клон только по тембру (x-vector)",
    "ref_hint": "💡 Реф: ~10 сек чистой речи без шума. Транскрипт (или кнопка распознавания) даёт лучший клон; язык лучше выставить явно.",
    "voice_preset": "Пресет голоса", "refresh": "🔄 Обновить", "transcribe_btn": "📝 Распознать транскрипт",
    "ph_clone": "Текст, который произнесёт клонированный голос…",
    "cloud_title": "☁️ Скачать голоса с сервера (русский пак)", "cloud_status": "Статус",
    "load_list": "Обновить список", "cloud_voices": "Доступные голоса",
    "download_sel": "⬇️ Скачать выбранные", "download_all": "⬇️ Скачать все 700+",
    "num_speakers": "Количество дикторов", "refresh_voices": "🔄 Обновить список голосов",
    "multi_hint": "Впиши/вставь диалог в формате `Speaker 0: реплика` / `Speaker 1: …`, задай каждому диктору голос и нажми «Озвучить». Номер = диктор ниже.",
    "script": "Сценарий (Speaker N: реплика)", "ph_script": "Speaker 0: Привет!\nSpeaker 1: Здравствуй!",
    "examples": "Примеры",
    "batch_text": "Список текстов (по одному в строке)", "ph_batch": "Первая фраза.\nВторая фраза.\nТретья фраза.",
    "log": "Лог", "brand_header_html": BRAND_HTML_RU,
}
_EN = {
    "tab_tts": "🎙️ TTS", "tab_clone": "🧬 Cloning",
    "tab_multi": "🎬 Multi-voice", "tab_batch": "📦 Batch",
    "text": "Text", "ph_text": "Type text to synthesize…",
    "tts_voice": "Voice (reference — required, else clicks)",
    "generate": "🔊 Generate", "stop": "⏹ Stop", "result": "Result", "advanced": "Advanced",
    "model": "Model", "precision": "Precision (VRAM)", "out_format": "Output format", "language": "Language",
    "steps": "Steps (mf = 4)", "guidance": "Guidance (CFG, >2 distorts)",
    "speaker_scale": "Reference timbre strength", "seed": "Seed (-1 = random)",
    "normalize": "Normalize numbers/dates (slower)",
    "guid_info": "soar/base only; mf has CFG fused (slider has no effect).",
    "spk_info": ">1.5 = closer to reference, but artifact risk.",
    "ref_voice": "Reference audio (voice)", "ref_text": "Reference transcript (for best clone)",
    "ph_ref_text": "What the reference says… empty = timbre-only clone (x-vector)",
    "ref_hint": "💡 Reference: ~10s of clean speech, no noise. A transcript (or the transcribe button) gives the best clone; set the language explicitly.",
    "voice_preset": "Voice preset", "refresh": "🔄 Refresh", "transcribe_btn": "📝 Transcribe reference",
    "ph_clone": "Text the cloned voice will speak…",
    "cloud_title": "☁️ Download voices from server (Russian pack)", "cloud_status": "Status",
    "load_list": "Refresh list", "cloud_voices": "Available voices",
    "download_sel": "⬇️ Download selected", "download_all": "⬇️ Download all 700+",
    "num_speakers": "Number of speakers", "refresh_voices": "🔄 Refresh voice list",
    "multi_hint": "Write/paste a dialogue as `Speaker 0: line` / `Speaker 1: …`, give each speaker a voice and hit Generate. The number = speaker below.",
    "script": "Script (Speaker N: line)", "ph_script": "Speaker 0: Hello!\nSpeaker 1: Hi there!",
    "examples": "Examples",
    "batch_text": "List of texts (one per line)", "ph_batch": "First line.\nSecond line.\nThird line.",
    "log": "Log", "brand_header_html": BRAND_HTML_EN,
}
I18N = gr.I18n(en=_EN, ru=_RU)


def T(key):
    return I18N(key)


HEAD_SCRIPT = """
<script>
(function(){
  var lang;
  try { lang = new URL(window.location).searchParams.get('__lang'); } catch(e) { lang = null; }
  if (!lang) return;
  try {
    Object.defineProperty(navigator, 'language',  {get: function(){ return lang; }, configurable: true});
    Object.defineProperty(navigator, 'languages', {get: function(){ return [lang]; }, configurable: true});
    document.documentElement.lang = lang;
  } catch(e) {}
  var sp = null;
  function getStore(){
    if (sp) return sp;
    var link = document.querySelector('link[href*="i18n-"]');
    if (!link) return null;
    sp = import(link.href).then(function(m){
      for (var k in m){ var v = m[k];
        try { if (v && typeof v.subscribe === 'function' && typeof v.set === 'function'){
          var c; var u = v.subscribe(function(x){ c = x; }); if (typeof u === 'function') u();
          if (typeof c === 'string' && /^[a-z]{2}(-[A-Za-z]+)?$/.test(c)) return v;
        }} catch(e) {}
      }
      return null;
    }).catch(function(){ return null; });
    return sp;
  }
  function apply(){
    var p = getStore(); if (!p) return;
    p.then(function(s){ if (s){ try { s.set(lang); window.dispatchEvent(new Event('languagechange')); } catch(e) {} } });
  }
  var n = 0, iv = setInterval(function(){ apply(); if (++n > 30) clearInterval(iv); }, 120);
  apply();
  document.addEventListener('click', function(e){
    try { if (e.target && e.target.closest && e.target.closest('[role=tablist],.tab-nav,[role=tab]')){
      setTimeout(apply, 60); setTimeout(apply, 250);
    }} catch(_) {}
  }, true);
})();
</script>
"""

CSS = """
.gradio-container {max-width: 1080px !important; margin: auto !important;}
.brand-header { position: relative; }
.brand-box { background: linear-gradient(135deg, #4c1d95 0%, #6d28d9 50%, #7e22ce 100%);
  padding: 24px 28px; border-radius: 16px; margin: 8px 0 16px 0;
  box-shadow: 0 10px 30px rgba(109,40,217,0.35); color: white; text-align: center; }
.brand-title { font-size: 1.9em; font-weight: 700; margin: 0 0 6px 0; }
.brand-subtitle { font-size: 1em; opacity: 0.9; margin-bottom: 14px; }
.brand-credits { font-size: 0.9em; opacity: 0.95; }
.brand-credits a { color:#fbbf24 !important; text-decoration:none !important; font-weight:600 !important; background:none !important; padding:0 !important; }
.brand-credits a:hover { text-decoration: underline !important; }
.device-badge { display:inline-block; background:rgba(255,255,255,0.15); padding:4px 12px; border-radius:999px; font-size:0.85em; margin-top:10px; }
.lang-switcher { position:absolute; top:12px; right:16px; display:flex; gap:6px; align-items:flex-start; z-index:50; }
.lang-btn { background:rgba(255,255,255,0.18); color:white !important; padding:5px 10px; border-radius:8px;
  font-size:0.82em; text-decoration:none !important; font-weight:600; display:inline-flex; flex-direction:column;
  align-items:center; justify-content:center; gap:2px; line-height:1; white-space:nowrap; min-width:44px; cursor:pointer; }
.lang-btn:hover { background:rgba(255,255,255,0.3); }
.lang-btn img { margin:0 !important; vertical-align:middle !important; }
.tabs > div[role="tablist"] > button, .tab-nav > button { flex:1 !important; text-align:center !important; }
.spk-block { background: rgba(124,58,237,0.06); border:1px solid rgba(124,58,237,0.25); border-radius:12px; padding:10px; margin:6px 0; }
.donate-wrap { position:relative; display:inline-block; }
.donate-wrap > summary.donate-btn { list-style:none; cursor:pointer; }
.donate-wrap > summary.donate-btn::-webkit-details-marker { display:none; }
.donate-wrap:not([open]) .donate-popover { display:none !important; pointer-events:none; }
.donate-popover { position:absolute; top:calc(100% + 6px); right:0; background:rgba(20,20,28,0.98);
  backdrop-filter:blur(8px); border:1px solid rgba(255,255,255,0.12); border-radius:10px; padding:10px 14px;
  min-width:320px; box-shadow:0 8px 24px rgba(0,0,0,0.4); z-index:999; font-size:13px; line-height:1.5; text-align:left; }
.donate-popover a { color:#c4a3ff !important; text-decoration:none !important; font-weight:600 !important; background:none !important; padding:0 !important; }
.donate-row { display:flex; justify-content:space-between; align-items:center; gap:10px; padding:4px 0; }
.donate-row > span { color:#9ca3af; font-weight:600; font-size:12px; flex:0 0 80px; text-align:left; white-space:nowrap; }
.donate-row > code { flex:1; text-align:left; background:rgba(255,255,255,0.06); padding:2px 6px; border-radius:4px; font-size:11px; color:#e5e7eb; user-select:all; }
.donate-intro { color:#cbd5e1; font-size:12px; line-height:1.5; margin:0 0 4px 0; }
.donate-sep { height:1px; background:rgba(255,255,255,0.1); margin:6px 0; }
.gradio-container { --block-border-color: rgba(255,255,255,0.10) !important;
  --border-color-primary: rgba(255,255,255,0.10) !important;
  --input-border-color: rgba(255,255,255,0.10) !important;
  --neutral-200: rgba(255,255,255,0.10) !important; }
.gradio-container .block { border-color: rgba(255,255,255,0.10) !important; }
.gradio-container input[type=range] { accent-color: #7c3aed; }
"""

DARK_JS = """
() => {
  try { const u=new URL(window.location);
    if(u.searchParams.get('__theme')!=='dark' && !sessionStorage.getItem('_dots_dark')){
      sessionStorage.setItem('_dots_dark','1'); u.searchParams.set('__theme','dark'); window.location.replace(u.href); return;
    } } catch(e){}
}
"""

TTS_EXAMPLES = [
    ["Привет! Это dots.tts Studio — локальная озвучка на ста с лишним языках."],
    ["Hello! This model speaks over a hundred languages, fully offline."],
    ["Сегодня отличный день, чтобы запустить нейросеть прямо у себя на компьютере."],
]
MULTI_EXAMPLES = [["Speaker 0: Привет! Как настроение?\nSpeaker 1: Отличное, только что собрал портативку!"]]

# ----------------------------------------------------------------------------
# Формат вывода / сохранение
# ----------------------------------------------------------------------------
_OUT_FORMAT = "mp3"
_FMT = {"wav": ("WAV", None), "mp3": ("MP3", None), "flac": ("FLAC", None), "ogg": ("OGG", "VORBIS")}


def set_out_format(f):
    global _OUT_FORMAT
    _OUT_FORMAT = f if f in _FMT else "wav"


def _save(sr, wav, prefix="tts"):
    import soundfile as sf
    if wav is None or len(wav) == 0:
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    container, subtype = _FMT.get(_OUT_FORMAT, ("WAV", None))
    path = OUTPUT_DIR / f"{prefix}_{stamp}.{_OUT_FORMAT}"
    try:
        sf.write(str(path), wav, sr, format=container, subtype=subtype)
    except Exception as e:
        print(f"[save] {_OUT_FORMAT} не записался ({e}) → wav")
        path = OUTPUT_DIR / f"{prefix}_{stamp}.wav"
        sf.write(str(path), wav, sr)
    return str(path)


# ----------------------------------------------------------------------------
# Голоса-пресеты
# ----------------------------------------------------------------------------
def scan_voices():
    exts = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
    return sorted(p.stem for p in VOICES_DIR.iterdir() if p.is_file() and p.suffix.lower() in exts)


def voice_path(name):
    for ext in (".wav", ".mp3", ".flac", ".ogg", ".m4a"):
        p = VOICES_DIR / f"{name}{ext}"
        if p.exists():
            return str(p)
    return None


def voice_transcript(name):
    for ext in (".txt", ".lab"):
        p = VOICES_DIR / f"{name}{ext}"
        if p.exists():
            for enc in ("utf-8", "cp1251"):
                try:
                    return p.read_text(encoding=enc).strip()
                except Exception:
                    continue
    return ""


def cb_preset(name):
    if not name or name == OWN_FILE:
        return None, ""
    return voice_path(name), voice_transcript(name)


def _clean_txt(t):
    return t if (isinstance(t, str) and t and not t.startswith("⚠")) else ""


def cb_prep_preset(name):
    """Пресет выбран → совпадающий транскрипт (обрезка 12с + Parakeet). Сам реф идёт из списка
    (cb_clone берёт voice_path), поэтому слот загрузки очищаем — он для СВОЕЙ записи/файла."""
    if not name or name == OWN_FILE:
        return None, ""
    clip, txt = _resolve_ref(voice_path(name), voice_transcript(name))   # длинный → обрезка 12с + Parakeet
    if not txt:
        txt = transcribe(clip)
    return None, _clean_txt(txt)


def cb_prep_upload(path):
    """Загрузка/запись СВОЕГО рефа → авто-транскрипт (обрезку длинного учтёт _resolve_ref на генерации).
    Файл оставляем в виджете как есть — нативная загрузка играется корректно."""
    if not path:
        return gr.update(), ""
    clip, txt = _resolve_ref(path, "")
    if not txt:
        txt = transcribe(clip)
    return gr.update(), _clean_txt(txt)


# ----------------------------------------------------------------------------
# ASR авто-транскрипт референса (Moonshine)
# ----------------------------------------------------------------------------
_ASR = None


def _get_asr():
    """NVIDIA Parakeet-TDT-0.6B-v3 (onnx-asr, int8 ~670 МБ, мультиязычный вкл. русский) — как в shorts-dub."""
    global _ASR
    if _ASR is None:
        import onnx_asr
        import onnxruntime as ort
        dev = "cpu"
        try:
            import torch
            dev = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            pass
        if dev == "cuda":
            try:
                ort.preload_dlls()   # подтянуть cufft/cublas/cudnn из nvidia-*-cu12 wheels
            except Exception:
                pass
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        else:
            providers = ["CPUExecutionProvider"]
        _ASR = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3", quantization="int8", providers=providers)
    return _ASR


def transcribe(ref_audio):
    if not ref_audio:
        return gr.update()
    if eng.DOTS_MOCK:
        return "пример транскрипта (mock)"
    try:
        import soundfile as sf
        import numpy as np
        import tempfile
        if _ASR is None:
            gr.Info("Первая загрузка ASR (Parakeet)… / Downloading ASR model…")
        m = _get_asr()
        # onnx_asr читает ТОЛЬКО RIFF/PCM-WAV ("file does not start with RIFF id" на mp3).
        # Декодируем сами (soundfile тянет mp3/flac/ogg) → моно → чистый WAV → распознаём.
        data, sr = sf.read(str(ref_audio), dtype="float32", always_2d=True)
        data = data.mean(axis=1)
        f = tempfile.NamedTemporaryFile(suffix="._asr.wav", delete=False, dir=os.environ.get("TEMP"))
        f.close()
        sf.write(f.name, data.astype(np.float32), sr)
        res = m.recognize(f.name)
        try:
            os.unlink(f.name)
        except Exception:
            pass
        txt = res if isinstance(res, str) else getattr(res, "text", str(res))
        return (txt or "").strip()
    except Exception as e:
        print(f"[asr] {e}")
        return "⚠️ Распознавание не удалось / ASR failed"


# Длинный реф щёлкает и перегенерит (доки: ~10с идеал). Обрезать без ре-транскрипта = рассинхрон.
# Поэтому: длинный реф → обрезка ~12с + ПЕРЕ-распознавание (Parakeet) → совпадающий короткий транскрипт.
_REF_RESOLVED = {}
_REF_TRIM_SEC = 12


def _ref_cache_key(ref_path, dur):
    """Стабильный ключ по содержимому файла (имя+размер+mtime+обрезка+длина) — переживает рестарт."""
    import hashlib
    st = os.stat(ref_path)
    raw = f"{os.path.basename(ref_path)}|{st.st_size}|{int(st.st_mtime)}|{_REF_TRIM_SEC}|{round(dur, 1)}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def _resolve_ref(ref_path, transcript):
    """Реф → (короткий реф, совпадающий транскрипт). Короткий — как есть; длинный — обрезка + ре-ASR.
    Кэш на диск (cache/refcache): тот же голос распознаётся Parakeet'ом один раз — даже после рестарта."""
    if not ref_path:
        return None, transcript
    try:
        import soundfile as sf
        info = sf.info(ref_path)
        dur = info.frames / max(info.samplerate, 1)
        if dur <= _REF_TRIM_SEC + 4:
            t = transcript or ""
            return ref_path, ("" if t.startswith("⚠") else t)   # ошибка ASR ≠ транскрипт
        mkey = (ref_path, round(dur, 1))
        if mkey in _REF_RESOLVED:               # горячий кэш (память)
            return _REF_RESOLVED[mkey]
        if eng.DOTS_MOCK:
            return ref_path, (transcript or "")
        ck = _ref_cache_key(ref_path, dur)
        cwav, ctxt = REF_CACHE_DIR / f"{ck}.wav", REF_CACHE_DIR / f"{ck}.txt"
        if cwav.exists() and ctxt.exists():      # диск-кэш: без повторного Parakeet
            res = (str(cwav), ctxt.read_text(encoding="utf-8"))
            _REF_RESOLVED[mkey] = res
            print(f"[ref] {os.path.basename(ref_path)}: кэш-хит (диск)", flush=True)
            return res
        import numpy as np
        data, sr = sf.read(ref_path, dtype="float32", always_2d=True)
        data = data[: int(sr * _REF_TRIM_SEC)].mean(axis=1)
        sf.write(str(cwav), data.astype(np.float32), sr)
        newtxt = transcribe(str(cwav))
        if not isinstance(newtxt, str) or newtxt.startswith("⚠"):
            newtxt = ""                          # ASR не вышел → x-vector (только тембр)
        ctxt.write_text(newtxt, encoding="utf-8")
        _REF_RESOLVED[mkey] = (str(cwav), newtxt)
        print(f"[ref] {os.path.basename(ref_path)}: {dur:.0f}с → {_REF_TRIM_SEC}с + Parakeet (закэшировано)", flush=True)
        return str(cwav), newtxt
    except Exception as e:
        print(f"[ref] resolve: {e}", flush=True)
        return ref_path, (transcript or "")


# ----------------------------------------------------------------------------
# Облачные голоса (Slait/russia_voices)
# ----------------------------------------------------------------------------
def cb_load_cloud():
    voices = []
    try:
        from huggingface_hub import list_repo_files
        files = list(list_repo_files(CLOUD_VOICES_REPO, repo_type="dataset"))
        voices = sorted(f[:-4] for f in files if f.endswith(".mp3"))
    except Exception as e:
        print(f"[voices] list: {e}")
    status = f"Найдено / Found: {len(voices)}" if voices else "Не удалось загрузить / Failed"
    return status, gr.update(choices=voices, value=[])


def _dl_voice(name):
    import requests
    try:
        r = requests.get(f"{CLOUD_VOICES_BASE}/{name}.mp3?download=true", timeout=90)
        r.raise_for_status()
        (VOICES_DIR / f"{name}.mp3").write_bytes(r.content)
        try:
            rt = requests.get(f"{CLOUD_VOICES_BASE}/{name}.txt?download=true", timeout=30)
            if rt.status_code == 200:
                (VOICES_DIR / f"{name}.txt").write_text(rt.text, encoding="utf-8")
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"[voices] dl {name}: {e}")
        return False


def cb_download_voices(selected):
    if not selected:
        return "Выберите голоса / Select voices", gr.update()
    ok = sum(_dl_voice(n) for n in selected)
    return f"Скачано / Downloaded: {ok}/{len(selected)}", gr.update(choices=[OWN_FILE] + scan_voices())


def cb_download_all_cloud(progress=gr.Progress()):
    try:
        from huggingface_hub import list_repo_files
        names = sorted(f[:-4] for f in list_repo_files(CLOUD_VOICES_REPO, repo_type="dataset") if f.endswith(".mp3"))
    except Exception as e:
        return f"Ошибка списка / List error: {e}", gr.update()
    if not names:
        return "Список пуст / Empty list", gr.update()
    ok = 0
    for i, name in enumerate(names):
        progress((i + 1) / len(names), desc=f"{i + 1}/{len(names)} · {name}")
        if _dl_voice(name):
            ok += 1
    return f"Скачано / Downloaded: {ok}/{len(names)}", gr.update(choices=[OWN_FILE] + scan_voices())


# ----------------------------------------------------------------------------
# Парсинг мульти-спикерного сценария
# ----------------------------------------------------------------------------
_SPK_PATTERNS = [r'^speaker\s*(\d+)\s*:\s*(.+)$', r'^диктор\s*(\d+)\s*:\s*(.+)$',
                 r'^голос\s*(\d+)\s*:\s*(.+)$', r'^\[(\d+)\]\s*(.+)$']


def parse_script(script):
    out = []
    for line in (script or "").strip().splitlines():
        line = line.strip()
        if not line:
            continue
        matched = False
        for pat in _SPK_PATTERNS:
            m = re.match(pat, line, re.IGNORECASE)
            if m:
                out.append((int(m.group(1)), m.group(2).strip()))
                matched = True
                break
        if not matched:
            out.append((0, line))
    return out


# ----------------------------------------------------------------------------
# Колбэки генерации
# ----------------------------------------------------------------------------
def _friendly(e):
    s = str(e).lower()
    if "out of memory" in s or ("cuda" in s and "memory" in s):
        return "Недостаточно VRAM — выберите float16 или короче текст / Out of VRAM — try float16 or shorter text."
    return f"Ошибка генерации / Generation error: {str(e)[:200]}"


def cb_tts(text, model, voice, language, steps, guidance, spk, normalize, seed):
    """Озвучка = синтез голосом-рефом (модель клонирующая, без рефа щёлкает). Без стриминга."""
    eng.clear_cancel()
    ref = voice_path(voice) if voice and voice != OWN_FILE else None
    rtext = voice_transcript(voice) if voice and voice != OWN_FILE else ""
    ref, rtext = _resolve_ref(ref, rtext)   # длинный реф → обрезка+ре-ASR (иначе щелчки/перегенерация)
    try:
        sr, wav = eng.synth_text(text, label=model, ref_audio=ref, ref_text=rtext, language=language,
                                 num_steps=steps, guidance_scale=guidance, speaker_scale=spk,
                                 normalize=normalize, seed=seed)
    except Exception as e:
        raise gr.Error(_friendly(e))
    _save(sr, wav, "tts")
    return (sr, wav)


def cb_clone(text, model, ref_audio, ref_text, preset, language, steps, guidance, spk, normalize, seed):
    """Клонирование (без стриминга): полный синтез + нормализация + сохранение."""
    eng.clear_cancel()
    ref = ref_audio or (voice_path(preset) if preset and preset != OWN_FILE else None)
    ref, ref_text = _resolve_ref(ref, ref_text)   # длинный реф → обрезка+ре-ASR (иначе щелчки/перегенерация)
    try:
        sr, wav = eng.synth_text(text, label=model, ref_audio=ref, ref_text=ref_text, language=language,
                                 num_steps=steps, guidance_scale=guidance, speaker_scale=spk,
                                 normalize=normalize, seed=seed)
    except Exception as e:
        raise gr.Error(_friendly(e))
    _save(sr, wav, "clone")
    return (sr, wav)


def cb_multi_synth(script, model, language, steps, guidance, spk, normalize, seed,
                   a0, a1, a2, a3, t0, t1, t2, t3, progress=gr.Progress()):
    """Парсим 'Speaker N:' → синтез каждой реплики голосом диктора N → LUFS-склейка."""
    eng.clear_cancel()
    audios, texts = [a0, a1, a2, a3], [t0, t1, t2, t3]
    parsed = [(sid, txt) for sid, txt in parse_script(script) if txt.strip()]
    if not parsed:
        return None
    turns = []
    for sid, txt in parsed:
        ref = audios[sid] if 0 <= sid < MAX_SPK else None
        rt = (texts[sid] if 0 <= sid < MAX_SPK else None) or None
        turns.append({"text": txt, "ref_audio": ref, "ref_text": rt})

    def _prog(i, n):
        progress((i + 1) / max(n, 1), desc=f"{i + 1}/{n}")
    try:
        sr, wav = eng.synth_turns(turns, label=model, language=language, num_steps=steps,
                                  guidance_scale=guidance, speaker_scale=spk, normalize=normalize,
                                  seed=seed, on_progress=_prog)
    except Exception as e:
        raise gr.Error(_friendly(e))
    _save(sr, wav, "multi")
    return (sr, wav)


def cb_batch(texts, model, language, steps, guidance, spk, normalize, seed, progress=gr.Progress()):
    eng.clear_cancel()
    lines = [t.strip() for t in (texts or "").splitlines() if t.strip()]
    log, paths = [], []
    for i, line in enumerate(lines):
        if eng.cancelled():
            yield "\n".join(log) + "\n\n⏹ Остановлено / Stopped.", paths
            return
        progress((i + 1) / max(len(lines), 1), desc=f"{i + 1}/{len(lines)}")
        try:
            sr, wav = eng.synth_text(line, label=model, language=language, num_steps=steps,
                                     guidance_scale=guidance, speaker_scale=spk, normalize=normalize, seed=seed)
        except Exception as e:
            raise gr.Error(_friendly(e))
        p = _save(sr, wav, "batch")
        if p:
            paths.append(p)
        log.append(f"✓ {i + 1}. {line[:60]}")
        yield "\n".join(log), paths
    yield "\n".join(log) + "\n\nГотово / Done.", paths


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
def _speaker_blocks():
    """4 блока диктора (пресет + аудио + транскрипт), показ по слайдеру."""
    with gr.Row():
        num = gr.Slider(2, MAX_SPK, value=2, step=1, label=T("num_speakers"))
        refresh = gr.Button(T("refresh_voices"), size="sm", scale=0)
    choices = [OWN_FILE] + scan_voices()
    blocks, audios, texts, pres = [], [], [], []
    for i in range(MAX_SPK):
        with gr.Group(visible=(i < 2), elem_classes="spk-block") as bl:
            gr.Markdown(f"**Speaker {i}**")
            pre = gr.Dropdown(choices, value=OWN_FILE, label=T("voice_preset"))
            au = gr.Audio(label=T("ref_voice"), type="filepath", sources=["upload", "microphone"])
            tx = gr.Textbox(label=T("ref_text"), lines=1, placeholder=T("ph_ref_text"))
            pre.change(cb_preset, [pre], [au, tx])
        blocks.append(bl)
        audios.append(au)
        texts.append(tx)
        pres.append(pre)
    num.change(lambda n: [gr.update(visible=(i < n)) for i in range(MAX_SPK)], [num], blocks)
    refresh.click(lambda: [gr.update(choices=[OWN_FILE] + scan_voices()) for _ in range(MAX_SPK)], None, pres)
    return num, audios, texts


def build():
    with gr.Blocks(title=APP_NAME) as demo:
        gr.HTML(T("brand_header_html"))
        with gr.Row():
            model_dd = gr.Dropdown(MODEL_CHOICES, value=eng.DEFAULT_MODEL, label=T("model"))
            lang_dd = gr.Dropdown(LANG_CHOICES, value="auto_detect", label=T("language"))
            prec_dd = gr.Dropdown([("bfloat16 — качество (дефолт)", "bfloat16"),
                                   ("float16 — экономнее VRAM", "float16"),
                                   ("float32 — максимум (много VRAM)", "float32")],
                                  value="bfloat16", label=T("precision"))
            fmt_dd = gr.Radio(["mp3", "wav", "flac", "ogg"], value="mp3", label=T("out_format"))
        prec_dd.change(lambda p: eng.set_precision(p), [prec_dd], None)
        fmt_dd.change(set_out_format, [fmt_dd], None)

        _mf0 = eng.is_mf(eng.DEFAULT_MODEL)

        def _adv():
            # старт под дефолтную модель: для mf шаги=4 и guidance заблокированы (CFG вшит в MeanFlow)
            steps = gr.Slider(1, 32, (4 if _mf0 else 24), step=1, label=T("steps"), interactive=not _mf0)
            guid = gr.Slider(1.0, 2.0, 1.2, step=0.1, label=T("guidance"), interactive=not _mf0, info=T("guid_info"))
            spk = gr.Slider(0.0, 3.0, 1.5, step=0.1, label=T("speaker_scale"), info=T("spk_info"))
            seed = gr.Number(-1, label=T("seed"), precision=0)
            norm = gr.Checkbox(label=T("normalize"), value=False)
            return steps, guid, spk, seed, norm

        with gr.Tabs():
            # 1. Озвучка — голос из списка ИЛИ свой реф + ASR (механизм один: модель клонирующая)
            with gr.Tab(T("tab_tts")):
                with gr.Row():
                    with gr.Column():
                        c_text = gr.Textbox(label=T("text"), placeholder=T("ph_clone"), lines=4)
                        _cv = scan_voices()
                        c_preset = gr.Dropdown([OWN_FILE] + _cv, value=(_DEF_VOICE if _DEF_VOICE in _cv else OWN_FILE), label=T("voice_preset"))
                        c_refresh = gr.Button(T("refresh"), size="sm")
                        c_ref = gr.Audio(label=T("ref_voice"), type="filepath", sources=["upload", "microphone"])
                        c_ref_text = gr.Textbox(label=T("ref_text"), lines=2, placeholder=T("ph_ref_text"))
                        c_tr_btn = gr.Button(T("transcribe_btn"), size="sm")
                        gr.Markdown(T("ref_hint"))
                        with gr.Accordion(T("advanced"), open=False):
                            c_steps, c_guid, c_spk, c_seed, c_norm = _adv()
                        c_btn = gr.Button(T("generate"), variant="primary", size="lg")
                        c_stop = gr.Button(T("stop"), variant="stop")
                    c_out = gr.Audio(label=T("result"), type="numpy", autoplay=True)
                gr.Examples(TTS_EXAMPLES, inputs=[c_text], label=T("examples"))
                with gr.Accordion(T("cloud_title"), open=False):
                    cl_status = gr.Textbox(label=T("cloud_status"), interactive=False)
                    with gr.Row():
                        cl_load = gr.Button(T("load_list"), size="sm")
                        cl_all = gr.Button(T("download_all"), size="sm")
                    cl_voices = gr.CheckboxGroup(choices=[], label=T("cloud_voices"))
                    cl_dl = gr.Button(T("download_sel"), variant="primary", size="sm")
                c_preset.change(cb_prep_preset, [c_preset], [c_ref, c_ref_text])
                c_ref.upload(cb_prep_upload, [c_ref], [c_ref, c_ref_text])
                c_ref.stop_recording(cb_prep_upload, [c_ref], [c_ref, c_ref_text])
                c_tr_btn.click(transcribe, [c_ref], [c_ref_text])
                c_refresh.click(lambda: gr.update(choices=[OWN_FILE] + scan_voices()), None, [c_preset])
                cl_load.click(cb_load_cloud, None, [cl_status, cl_voices])
                cl_all.click(cb_download_all_cloud, None, [cl_status, c_preset])
                cl_dl.click(cb_download_voices, [cl_voices], [cl_status, c_preset])
                ev_clone = c_btn.click(cb_clone, [c_text, model_dd, c_ref, c_ref_text, c_preset, lang_dd,
                                                  c_steps, c_guid, c_spk, c_norm, c_seed], [c_out])
                c_stop.click(eng.request_cancel, None, None, queue=False, cancels=[ev_clone])

            # 3. Мульти-голос (ручной Speaker N:)
            with gr.Tab(T("tab_multi")):
                gr.Markdown(T("multi_hint"))
                m_num, m_audios, m_texts = _speaker_blocks()
                m_script = gr.Textbox(label=T("script"), placeholder=T("ph_script"), lines=9)
                gr.Examples(MULTI_EXAMPLES, inputs=[m_script], label=T("examples"))
                with gr.Accordion(T("advanced"), open=False):
                    m_steps, m_guid, m_spk, m_seed, m_norm = _adv()
                m_btn = gr.Button(T("generate"), variant="primary", size="lg")
                m_stop = gr.Button(T("stop"), variant="stop")
                m_out = gr.Audio(label=T("result"), type="numpy", autoplay=True)
                ev_multi = m_btn.click(
                    cb_multi_synth,
                    [m_script, model_dd, lang_dd, m_steps, m_guid, m_spk, m_norm, m_seed] + m_audios + m_texts, [m_out])
                m_stop.click(eng.request_cancel, None, None, queue=False, cancels=[ev_multi])

            # 4. Пакет
            with gr.Tab(T("tab_batch")):
                bt_text = gr.Textbox(label=T("batch_text"), placeholder=T("ph_batch"), lines=6)
                with gr.Accordion(T("advanced"), open=False):
                    bt_steps, bt_guid, bt_spk, bt_seed, bt_norm = _adv()
                bt_btn = gr.Button(T("generate"), variant="primary", size="lg")
                bt_stop = gr.Button(T("stop"), variant="stop")
                bt_log = gr.Textbox(label=T("log"), lines=8)
                bt_files = gr.Files(label=T("result"))
                ev_batch = bt_btn.click(cb_batch, [bt_text, model_dd, lang_dd, bt_steps, bt_guid, bt_spk, bt_norm, bt_seed],
                                        [bt_log, bt_files])
                bt_stop.click(eng.request_cancel, None, None, queue=False, cancels=[ev_batch])

        # Смена модели → подходящие настройки: для mf шаги=4 И guidance заблокированы (CFG вшит),
        # soar/base — шаги 24 (тест: @10 слабо 0.66, @24≈0.92, @32 0.95) и guidance активны.
        def _model_settings(label):
            mf = eng.is_mf(label)
            steps_u = gr.update(value=(4 if mf else 24), interactive=not mf)
            guid_u = gr.update(interactive=not mf)
            return [steps_u, steps_u, steps_u, guid_u, guid_u, guid_u]
        model_dd.change(_model_settings, [model_dd],
                        [c_steps, m_steps, bt_steps, c_guid, m_guid, bt_guid])

        # первая загрузка страницы → подготовить дефолт-голос (обрезка + транскрипт видны сразу,
        # без demo.load c_preset.change не срабатывает и реф/транскрипт пустые)
        demo.load(cb_prep_preset, [c_preset], [c_ref, c_ref_text])

    return demo


def prewarm():
    """Загрузить дефолтную модель на старте (первый раз — докачка ~5 ГБ, видно в терминале)."""
    if eng.DOTS_MOCK or os.environ.get("DOTS_NO_PREWARM", "").lower() in ("1", "true", "yes"):
        return
    try:
        print("[prewarm] загрузка модели на старте...", flush=True)
        eng.get_runtime(eng.DEFAULT_MODEL)   # только загрузка (compile нет); без мусорной генерации
        try:
            cb_prep_preset(_DEF_VOICE)        # прогреть дефолт-голос (обрезка+Parakeet→диск-кэш) → первая загрузка UI мгновенная
        except Exception as e:
            print(f"[prewarm] голос: {e}", flush=True)
        print("[prewarm] готово — модель в памяти", flush=True)
    except Exception as e:
        print(f"[prewarm] пропущен ({e})", flush=True)


if __name__ == "__main__":
    print(f"[{APP_NAME}] {DEVICE_INFO}")
    prewarm()
    build().queue(default_concurrency_limit=1).launch(
        server_name="127.0.0.1", server_port=None,
        allowed_paths=[str(VOICES_DIR), str(REF_CACHE_DIR), str(OUTPUT_DIR)],   # иначе gradio не отдаёт реф-аудио из этих папок (плеер 0:00)
        inbrowser=(not eng.DOTS_MOCK and os.environ.get("NO_AUTO_BROWSER", "").lower() not in ("1", "true", "yes")),
        i18n=I18N, theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="purple"),
        css=CSS, js=DARK_JS, head=HEAD_SCRIPT, show_error=True)
