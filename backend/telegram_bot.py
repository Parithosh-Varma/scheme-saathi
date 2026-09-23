"""Telegram demo bot (polling, plain requests — no extra deps).

Setup:
  1. Chat with @BotFather on Telegram → /newbot → copy the token.
  2. Put it in backend/.env as TELEGRAM_BOT_TOKEN=<token>.
  3. Run:  python3 -m backend.telegram_bot   (from repo root)

Supports text + voice notes. Voice needs OPENAI_API_KEY; without it,
the bot asks for text (RAG itself works fully offline).
"""
import os
import time
import requests

from .config import DATABASE_URL  # noqa: F401  (ensures env loaded)
from .rag_engine import run_rag
from .voice_pipeline import transcribe_voice, synthesize_speech

API = "https://api.telegram.org/bot{token}/{method}"

START_MSG = (
    "Namaste! Main *SchemeSaathi* hoon.\n\n"
    "Mujhe apne baare mein batayein — text ya voice note mein — "
    "jaise:\n"
    "\"Main ek 30 saal ki mahila hu, gaon mein rehti hu, 2 bache hai\"\n\n"
    "Main aapko batata hoon aap kaun si sarkari yojanaon ke liye eligible hain."
)


def _call(token: str, method: str, **kwargs):
    r = requests.post(API.format(token=token, method=method), timeout=40, **kwargs)
    r.raise_for_status()
    return r.json()["result"]


def format_reply(result: dict) -> str:
    lang = result.get("language_detected", "hi")
    schemes = result.get("schemes", [])
    head = (f"Aapke liye {len(schemes)} yojana mili:" if lang == "hi"
            else f"Found {len(schemes)} schemes for you:")
    lines = [head]
    for i, s in enumerate(schemes, 1):
        lines.append(
            f"\n*{i}. {s['name']}*\n"
            f"Benefit: {s['benefit']}\n"
            f"Why: {s['eligibility_match']}\n"
            f"Docs: {', '.join(s['documents'])}\n"
            f"Apply: {s['apply_url']}"
        )
    lines.append(f"\n_{result.get('voice_response', '')}_")
    return "\n".join(lines)


def send_long(token: str, chat_id: int, text: str):
    for chunk in [text[i:i + 4000] for i in range(0, len(text), 4000)] or ["..."]:
        _call(token, "sendMessage", json={"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"})


def download_voice(token: str, file_id: str) -> bytes:
    info = _call(token, "getFile", json={"file_id": file_id})
    path = info["file_path"]
    r = requests.get(f"https://api.telegram.org/file/bot{token}/{path}", timeout=60)
    r.raise_for_status()
    return r.content


def handle_message(token: str, msg: dict):
    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()
    if text.startswith("/start"):
        send_long(token, chat_id, START_MSG)
        return
    if "voice" in msg or "audio" in msg:
        media = msg.get("voice") or msg.get("audio") or {}
        try:
            audio = download_voice(token, media["file_id"])
        except Exception:
            send_long(token, chat_id, "Voice download fail hui. Text mein likh kar bhejein.")
            return
        try:
            query = transcribe_voice(audio)
        except RuntimeError:
            send_long(token, chat_id,
                      "Voice ke liye OPENAI_API_KEY chahiye. Kripya text mein likh kar bhejein.")
            return
    elif text:
        query = text
    else:
        send_long(token, chat_id, "Kripya text ya voice note bhejein.")
        return
    try:
        result = run_rag(query)
    except Exception as e:
        send_long(token, chat_id, f"Maaf kijiye, kuch problem hui: {e}")
        return
    send_long(token, chat_id, format_reply(result))
    try:
        lang = result.get("language_detected", "hi")
        voice_out = synthesize_speech(result.get("voice_response", ""), lang)
        if voice_out:
            _call(token, "sendVoice", files={"voice": ("reply.mp3", voice_out, "audio/mpeg")},
                  data={"chat_id": chat_id})
    except Exception:
        pass


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token or token.startswith("PASTE"):
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in backend/.env (get one from @BotFather).")
    me = _call(token, "getMe")
    print(f"Bot running as @{me['username']}. Send /start in Telegram. Ctrl+C to stop.")
    offset = 0
    while True:
        try:
            updates = _call(token, "getUpdates",
                             json={"offset": offset, "timeout": 30,
                                   "allowed_updates": ["message"]})
        except Exception as e:
            print("poll error:", e)
            time.sleep(3)
            continue
        for u in updates:
            offset = u["update_id"] + 1
            if "message" in u:
                try:
                    handle_message(token, u["message"])
                except Exception as e:
                    print("handle error:", e)


if __name__ == "__main__":
    main()
