"""Meta WhatsApp Cloud API helpers (plain requests, no SDK)."""
import requests
from .config import WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN, GRAPH_API_VERSION

BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def verify_webhook(mode: str, token: str, challenge: str):
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return True, challenge
    return False, "verification failed"


def _headers():
    return {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}


def send_text_message(phone: str, text: str) -> dict:
    url = f"{BASE}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": text[:4000]}}
    r = requests.post(url, headers=_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def send_audio_message(phone: str, audio_bytes: bytes) -> dict:
    media_id = upload_media(audio_bytes, mime="audio/mpeg")
    url = f"{BASE}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {"messaging_product": "whatsapp", "to": phone,
               "type": "audio", "audio": {"id": media_id}}
    r = requests.post(url, headers=_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def upload_media(data: bytes, mime: str = "audio/mpeg") -> str:
    url = f"{BASE}/{WHATSAPP_PHONE_NUMBER_ID}/media"
    files = {"file": ("audio.mp3", data, mime)}
    r = requests.post(url, headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}, files=files, timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def download_media(media_id: str) -> bytes:
    info = requests.get(f"{BASE}/{media_id}", headers=_headers(), timeout=10).json()
    url = info["url"]
    r = requests.get(url, headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.content


def send_interactive_buttons(phone: str, schemes: list) -> dict:
    url = f"{BASE}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    buttons = []
    for s in schemes[:3]:
        buttons.append({"type": "reply", "reply": {"id": f"info_{s.get('scheme_id', '')[:20]}", "title": (s.get("name") or "")[:20]}})
    payload = {"messaging_product": "whatsapp", "to": phone, "type": "interactive",
               "interactive": {"type": "button", "body": {"text": "Aap inme se kisi ki details dekhna chahenge?"}, "action": {"buttons": buttons}}}
    r = requests.post(url, headers=_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def parse_incoming(payload: dict):
    """Return {phone, type, text, media_id} or None."""
    try:
        entry = payload["entry"][0]["changes"][0]["value"]
        msg = entry["messages"][0]
        phone = msg["from"]
        mtype = msg.get("type")
        if mtype == "text":
            return {"phone": phone, "type": "text", "text": msg["text"]["body"], "media_id": None}
        if mtype == "audio":
            return {"phone": phone, "type": "audio", "text": "", "media_id": msg["audio"]["id"]}
        return {"phone": phone, "type": mtype, "text": "", "media_id": None}
    except Exception:
        return None
