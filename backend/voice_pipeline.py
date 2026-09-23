"""STT via Whisper, TTS via gTTS, translation via Gemini. All have offline fallbacks."""
import io

LANG_MAP = {"hi": "hi", "en": "en", "ta": "ta", "bn": "bn", "mr": "mr", "te": "te", "kn": "kn"}


def detect_language(text: str) -> str:
    t = text or ""
    if any("\u0900" <= c <= "\u097f" for c in t):
        return "hi"
    if any("\u0b80" <= c <= "\u0bff" for c in t):
        return "ta"
    if any("\u0980" <= c <= "\u09ff" for c in t):
        return "bn"
    if any("\u0900" <= c <= "\u097f" for c in t):
        return "hi"
    low = t.lower()
    if any(w in low for w in ["main", "hun", "hu ", "meri", "mera", "kaise", "kya", "hai", "gaon", "saal", "mahila", "yojana"]):
        return "hi"
    return "en"


def transcribe_voice(audio_bytes: bytes, language: str = "") -> str:
    """Use OpenAI Whisper API if key present, else raise with helpful message."""
    import os
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set - send text query in demo mode instead.")
    from openai import OpenAI
    client = OpenAI(api_key=key, timeout=10)
    buf = io.BytesIO(audio_bytes)
    buf.name = "audio.ogg"
    kwargs = {"model": "whisper-1", "file": buf}
    if language:
        kwargs["language"] = language
    resp = client.audio.transcriptions.create(**kwargs)
    return resp.text


def synthesize_speech(text: str, language: str = "hi") -> bytes:
    """gTTS -> mp3 bytes. Falls back to empty bytes on failure."""
    try:
        from gtts import gTTS
        lang = LANG_MAP.get(language, "hi")
        tts = gTTS(text=text[:500], lang=lang if lang in ("hi", "en", "ta", "bn", "mr", "te", "kn") else "hi")
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        return buf.getvalue()
    except Exception:
        return b""


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    import os
    key = os.getenv("GEMINI_API_KEY", "")
    if not key or source_lang == target_lang:
        return text
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        r = model.generate_content(f"Translate from {source_lang} to {target_lang}. Return only translation:\n{text}",
                                    request_options={"timeout": 10})
        return (r.text or text).strip()
    except Exception:
        return text
