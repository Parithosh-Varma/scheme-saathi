import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "schemesaathi2025")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./schemesaathi.db")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
GRAPH_API_VERSION = "v21.0"
LLM_TIMEOUT = 10
RATE_LIMIT_PER_MIN = 10
# Free LLM via your opencode-proxy (OpenAI-compatible). Falls back to GEMINI_API_KEY, then offline rules.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8788/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "anything")
LLM_CHAT_MODEL = os.getenv("LLM_CHAT_MODEL", "mimo-v2.6-flash-free")
