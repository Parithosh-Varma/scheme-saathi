# 🪔 SchemeSaathi — Voice-First AI for India's Welfare Schemes

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](backend/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](backend/main.py)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](dashboard/)
[![WhatsApp Cloud API](https://img.shields.io/badge/WhatsApp-Cloud_API-25D366.svg)](backend/whatsapp.py)
[![Gemini 1.5 Flash](https://img.shields.io/badge/LLM-Gemini_1.5_Flash-4285F4.svg)](backend/rag_engine.py)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/Parithosh-Varma/scheme-saathi/pulls)

> **Rural citizens send a WhatsApp voice note in any Indian language → instantly get personalized government scheme recommendations they're eligible for — with benefit amounts, documents needed, and apply links.**

🎥 **2-min demo video:** _coming soon_ · 📊 **Live dashboard:** `http://localhost:3000` · 📖 **API docs:** `http://localhost:8000/docs`

---

## ✨ Why SchemeSaathi?

- 🎙️ **Voice-to-voice AI** — speaks Hindi, Tamil, Bengali, Marathi & more. No literacy barrier.
- 🧠 **RAG over 72 real schemes** — PM-KISAN, Ayushman Bharat, PMAY, Ladli Behna, MGNREGA… never hallucinated.
- ✅ **Eligibility-checked** — age, gender, caste, occupation, location matched per scheme, ranked by benefit.
- 🌐 **Code-mixed input** — understands Hinglish like _"main farmer hu"_.
- 📊 **Impact dashboard** — beneficiaries helped, top schemes, language split, auto-refresh.
- 🔌 **Works without keys** — offline TF-IDF + rule engine fallback, so the demo never dies on stage.

## 🏗️ Architecture

```
WhatsApp voice/text
        │
        ▼
┌──────────────┐   Whisper STT    ┌─────────────────────────┐
│  /webhook    │ ───────────────▶ │  RAG: Chroma + Gemini   │
│  FastAPI     │                  │  1.5 Flash + eligibility│
└──────────────┘ ◀─────────────── │  ranker (72 schemes)    │
        │      gTTS voice + buttons └─────────────────────────┘
        ▼                                        │
┌──────────────┐                          ┌──────────────┐
│ SQLite logs  │ ───────────────────────▶ │ Next.js      │
│ users/queries│      /api/analytics      │ dashboard    │
└──────────────┘                          └──────────────┘
Demo (no WhatsApp): POST /api/demo with text or audio → JSON + voice mp3
```

## 🚀 Quickstart (3 steps)

```bash
# 1. Configure
cp backend/.env.example backend/.env   # add OPENAI_API_KEY + GEMINI_API_KEY (optional — demo works without)

# 2. Run
docker-compose up --build              # backend :8000 · dashboard :3000

# 3. Try it (no WhatsApp needed)
curl -X POST http://localhost:8000/api/demo \
  -F "query=Main ek 30 saal ki mahila hu, gaon mein rehti hu, 2 bache hai"
```

Local dev alternative:
```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
python -m backend.seed_schemes   # populate Chroma vectors (optional)
```

## 💬 WhatsApp setup

1. Meta App → WhatsApp Cloud API → copy token + phone number ID into `backend/.env`
2. Webhook URL `https://<your-domain>/webhook`, verify token = `WHATSAPP_VERIFY_TOKEN`
3. Subscribe to `messages` → send a voice note → get schemes back, spoken aloud 🎙️

## 🛠️ Tech stack

| Layer | Tech |
|---|---|
| Backend | FastAPI · Python 3.11 |
| AI | LangChain · Gemini 1.5 Flash · OpenAI `text-embedding-3-small` |
| Retrieval | ChromaDB (persistent) + TF-IDF fallback |
| Voice | Whisper STT · gTTS TTS |
| Messaging | WhatsApp Cloud API (plain `requests`, no SDK) |
| Data | SQLite + SQLAlchemy · 72 verified schemes |
| Frontend | Next.js 14 App Router · Tailwind |
| Deploy | Docker + docker-compose |

## 📡 API

| Endpoint | Purpose |
|---|---|
| `GET /webhook` | Meta verification challenge |
| `POST /webhook` | Incoming WhatsApp messages |
| `POST /api/demo` | Text/audio → schemes + voice mp3 (no WhatsApp needed) |
| `GET /api/analytics` | Dashboard data |
| `GET /health` | Health check |

## 🗺️ Roadmap

- [ ] More languages (Telugu, Kannada, Malayalam, Odia)
- [ ] MyScheme.gov.in live scraper cron
- [ ] Apply-form autofill assistance
- [ ] IVR / missed-call fallback for non-smartphones

## 🤝 Contributing

PRs welcome! See open issues, fork, branch, PR. Run `python3 -m py_compile backend/*.py` before pushing.

## 📄 License

MIT — see [LICENSE](LICENSE).

---

<p align="center">Built for the hackathon in 36 hours. If it helps one family find one scheme, it worked. 🇮🇳</p>
