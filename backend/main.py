"""FastAPI app: WhatsApp webhook + demo endpoint + analytics."""
import time
from collections import Counter
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from .config import WHATSAPP_VERIFY_TOKEN, RATE_LIMIT_PER_MIN
from .database import get_db, init_db
from .models import UserSession, QueryLog
from .rag_engine import run_rag
from .voice_pipeline import transcribe_voice, synthesize_speech, detect_language

app = FastAPI(title="SchemeSaathi API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_rate: dict[str, list[float]] = {}


def check_rate(phone: str):
    now = time.time()
    hist = _rate.get(phone, [])
    hist = [t for t in hist if now - t < 60]
    if len(hist) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(429, "Rate limit: 10 requests/minute. Please wait.")
    hist.append(now)
    _rate[phone] = hist


def log_query(db: Session, phone: str, input_type: str, lang: str, qtext: str, result: dict, ms: int):
    try:
        user = db.query(UserSession).filter_by(phone_number=phone).first()
        if not user:
            user = UserSession(phone_number=phone, language_preference=lang)
            db.add(user)
            db.commit()
            db.refresh(user)
        user.last_active = datetime.utcnow()
        user.query_count = (user.query_count or 0) + 1
        schemes = result.get("schemes", [])
        db.add(QueryLog(user_id=user.id, phone_number=phone, input_type=input_type,
                        input_language=lang, query_text=qtext[:2000],
                        schemes_matched=len(schemes),
                        scheme_ids=[s.get("scheme_id", s.get("name", "")) for s in schemes],
                        response_time_ms=ms))
        db.commit()
    except Exception:
        db.rollback()


@app.on_event("startup")
def _startup():
    init_db()


# Ensure tables exist even if startup event is skipped (e.g. tests)
try:
    init_db()
except Exception:
    pass


@app.get("/")
def root():
    return {"service": "SchemeSaathi", "docs": "/docs", "health": "/health",
            "demo": "POST /api/demo", "analytics": "/api/analytics"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "SchemeSaathi"}


@app.get("/webhook")
def verify(mode: str = "", hub_mode: str = "", hub_verify_token: str = "", hub_challenge: str = ""):
    token = hub_verify_token
    challenge = hub_challenge
    if (hub_mode or mode) == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(challenge)
    raise HTTPException(403, "verification failed")


@app.post("/webhook")
async def incoming(req: Request, db: Session = Depends(get_db)):
    from . import whatsapp as wa
    payload = await req.json()
    parsed = wa.parse_incoming(payload)
    if not parsed:
        return {"status": "ignored"}
    phone = parsed["phone"]
    try:
        check_rate(phone)
    except HTTPException:
        wa.send_text_message(phone, "Kripya 1 minute ruk kar phir bhejein (rate limit).")
        return {"status": "rate-limited"}
    t0 = time.time()
    try:
        if parsed["type"] == "audio" and parsed.get("media_id"):
            audio = wa.download_media(parsed["media_id"])
            try:
                qtext = transcribe_voice(audio)
                itype = "voice"
            except RuntimeError as e:
                wa.send_text_message(phone, str(e))
                return {"status": "no-stt-key"}
        elif parsed["type"] == "text":
            qtext = parsed["text"]
            itype = "text"
        else:
            wa.send_text_message(phone, "Kripya text ya voice note bhejein.")
            return {"status": "unsupported-type"}
        result = run_rag(qtext)
        lang = result.get("language_detected", "hi")
        lines = [f"Namaste! Aapke liye {len(result['schemes'])} yojana mili:" if lang == "hi"
                 else f"Found {len(result['schemes'])} schemes for you:"]
        for i, s in enumerate(result["schemes"], 1):
            lines.append(f"\n{i}. {s['name']}\n   Benefit: {s['benefit']}\n   Why: {s['eligibility_match']}\n   Docs: {', '.join(s['documents'])}\n   Apply: {s['apply_url']}")
        lines.append(f"\n{result.get('voice_response', '')}")
        wa.send_text_message(phone, "\n".join(lines)[:4000])
        try:
            audio_out = synthesize_speech(result.get("voice_response", ""), lang)
            if audio_out:
                wa.send_audio_message(phone, audio_out)
        except Exception:
            pass
        ms = int((time.time() - t0) * 1000)
        log_query(db, phone, itype, lang, qtext, result, ms)
        return {"status": "ok"}
    except Exception as e:
        try:
            wa.send_text_message(phone, "Maaf kijiye, kuch technical problem hui. Kripya phir se try karein.")
        except Exception:
            pass
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)


@app.post("/api/demo")
async def demo(query: Optional[str] = Form(None), audio: Optional[UploadFile] = File(None),
               db: Session = Depends(get_db)):
    """Demo endpoint: accepts text query OR audio file. No WhatsApp credentials needed."""
    t0 = time.time()
    check_rate("demo")
    if audio is not None:
        data = await audio.read()
        if len(data) > 5 * 1024 * 1024:
            raise HTTPException(400, "Audio too long (max ~5MB / 2 min). Send a shorter voice note.")
        try:
            qtext = transcribe_voice(data)
            itype = "voice"
        except RuntimeError:
            raise HTTPException(400, "Voice needs OPENAI_API_KEY. Send text 'query' instead for offline demo.")
    elif query:
        qtext = query
        itype = "text"
    else:
        raise HTTPException(400, "Send 'query' text field or 'audio' file.")
    try:
        result = run_rag(qtext)
    except Exception as e:
        raise HTTPException(500, f"RAG failed: {e}")
    lang = result.get("language_detected", detect_language(qtext))
    audio_b64 = None
    try:
        ab = synthesize_speech(result.get("voice_response", ""), lang)
        if ab:
            import base64
            audio_b64 = base64.b64encode(ab).decode()
    except Exception:
        pass
    ms = int((time.time() - t0) * 1000)
    log_query(db, "demo", itype, lang, qtext, result, ms)
    return {"query": qtext, "input_type": itype, "response_time_ms": ms,
            "result": result, "audio_mp3_base64": audio_b64}


@app.get("/api/analytics")
def analytics(db: Session = Depends(get_db)):
    total_queries = db.query(func.count(QueryLog.id)).scalar() or 0
    total_users = db.query(func.count(UserSession.id)).scalar() or 0
    langs = Counter([r[0] for r in db.query(QueryLog.input_language).all() if r[0]])
    all_ids: list[str] = []
    for r in db.query(QueryLog.scheme_ids).all():
        if r[0]:
            all_ids.extend(r[0])
    top = Counter(all_ids).most_common(5)
    recent = db.query(QueryLog).order_by(QueryLog.created_at.desc()).limit(10).all()
    return {
        "total_beneficiaries": total_users,
        "total_queries": total_queries,
        "top_schemes": [{"scheme_id": k, "count": v} for k, v in top],
        "language_distribution": dict(langs),
        "recent_queries": [{"query": (q.query_text or '')[:80], "language": q.input_language,
                            "schemes_matched": q.schemes_matched,
                            "created_at": q.created_at.isoformat() if q.created_at else None} for q in recent],
    }
