"""LLM access: opencode-proxy (OpenAI-compatible, free) first, direct Gemini second.

Set in backend/.env:
  LLM_BASE_URL=http://127.0.0.1:8788/v1   (your opencode-proxy)
  LLM_API_KEY=anything                    (proxy needs no real key)
  LLM_CHAT_MODEL=mimo-v2.6-flash-free
Start the proxy with:  node proxy.mjs   (in your opencode-proxy folder)
"""
import os
import requests


def proxy_config() -> dict:
    return {
        "base_url": os.getenv("LLM_BASE_URL", "http://127.0.0.1:8788/v1").rstrip("/"),
        "api_key": os.getenv("LLM_API_KEY", "anything"),
        "model": os.getenv("LLM_CHAT_MODEL", "mimo-v2.6-flash-free"),
    }


def proxy_chat(prompt: str, timeout: int = 10, model: str = "") -> str:
    cfg = proxy_config()
    r = requests.post(
        f"{cfg['base_url']}/chat/completions",
        json={"model": model or cfg["model"],
              "messages": [{"role": "user", "content": prompt}],
              "stream": False},
        headers={"Authorization": f"Bearer {cfg['api_key']}"},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def proxy_available(timeout: int = 3) -> bool:
    try:
        r = requests.get(f"{proxy_config()['base_url']}/models", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def gemini_chat(prompt: str, timeout: int = 10):
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        return None
    import google.generativeai as genai
    genai.configure(api_key=key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    r = model.generate_content(prompt, request_options={"timeout": timeout})
    return (r.text or "").strip() or None


def chat(prompt: str, timeout: int = 10):
    """Try opencode-proxy first, then direct Gemini. Returns text or None."""
    try:
        text = proxy_chat(prompt, timeout=timeout)
        if text and text.strip():
            return text.strip()
    except Exception:
        pass
    try:
        return gemini_chat(prompt, timeout=timeout)
    except Exception:
        return None
