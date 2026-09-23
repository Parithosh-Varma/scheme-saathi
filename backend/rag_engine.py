"""RAG engine: ChromaDB + OpenAI embeddings when keys exist, else TF-IDF fallback. Gemini refines when key exists."""
import json
import os
import re
from pathlib import Path

from .eligibility import extract_profile, rank_schemes
from .prompts import VOICE_GREETINGS

from typing import Optional

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "schemes_seed.json"

_schemes_cache: Optional[list] = None
_chroma_collection = None


def load_schemes() -> list[dict]:
    global _schemes_cache
    if _schemes_cache is None:
        with open(DATA_PATH, encoding="utf-8") as f:
            _schemes_cache = json.load(f)
    return _schemes_cache


def _get_chroma():
    global _chroma_collection
    if _chroma_collection is not None:
        return _chroma_collection
    try:
        import chromadb
        from .config import CHROMA_PERSIST_DIR
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _chroma_collection = client.get_collection("indian_govt_schemes")
        return _chroma_collection
    except Exception:
        return None


def retrieve(query: str, k: int = 5) -> list:
    schemes = load_schemes()
    # Try Chroma vector search first
    try:
        if os.getenv("OPENAI_API_KEY"):
            from openai import OpenAI
            col = _get_chroma()
            if col is not None:
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=10)
                emb = client.embeddings.create(model="text-embedding-3-small", input=query).data[0].embedding
                res = col.query(query_embeddings=[emb], n_results=k)
                ids = (res.get("ids") or [[]])[0]
                by_id = {s["scheme_id"]: s for s in schemes}
                found = [by_id[i] for i in ids if i in by_id]
                if found:
                    return found
    except Exception:
        pass
    # TF-IDF fallback
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        def doc(s):
            return " ".join([s.get("name_en", ""), s.get("description", ""), s.get("benefit_amount", ""),
                             " ".join(s.get("tags", [])), " ".join(s.get("category", [])),
                             json.dumps(s.get("eligibility_criteria", {}))])
        docs = [doc(s) for s in schemes]
        vec = TfidfVectorizer(stop_words="english")
        mat = vec.fit_transform(docs + [query])
        sims = cosine_similarity(mat[-1], mat[:-1])[0]
        idx = sims.argsort()[::-1][:k]
        return [schemes[i] for i in idx]
    except Exception:
        # naive keyword overlap fallback (no sklearn)
        q = query.lower()
        def kw_score(s):
            blob = (s.get("name_en", "") + " " + s.get("description", "") + " " + " ".join(s.get("tags", []))).lower()
            return sum(1 for w in re.findall(r"\w{3,}", q) if w in blob)
        return sorted(schemes, key=kw_score, reverse=True)[:k]


def _gemini_refine(query: str, profile: dict, candidates: list, lang: str) -> Optional[dict]:
    # Free path: opencode-proxy (OpenAI-compatible) → direct Gemini → None (rule-based output)
    try:
        from .llm import chat
        from .prompts import RAG_SYSTEM_PROMPT
        docs = "\n".join([f"- {c['scheme_id']}: {c['name_en']} | {c['description']} | Benefit: {c['benefit_amount']} | Criteria: {json.dumps(c['eligibility_criteria'])} | Docs: {', '.join(c['documents_required'])} | URL: {c['application_url']}" for c in candidates])
        prompt = RAG_SYSTEM_PROMPT + f"\n\nUser query: {query}\nExtracted profile: {json.dumps(profile)}\nRetrieved documents:\n{docs}\n\nReturn strict JSON only."
        text = chat(prompt, timeout=30)
        if not text:
            return None
        text = text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception:
        return None


def run_rag(query: str) -> dict:
    from .voice_pipeline import detect_language
    lang = detect_language(query)
    profile = extract_profile(query)
    candidates = retrieve(query, k=10)
    ranked = rank_schemes(candidates, profile, top_k=3)
    # Gemini refine if available
    refined = _gemini_refine(query, profile, candidates[:5], lang)
    if refined and isinstance(refined.get("schemes"), list) and refined["schemes"]:
        refined.setdefault("language_detected", lang)
        refined.setdefault("user_profile", profile)
        return refined
    # Rule-based structured output
    schemes_out = []
    for item in ranked:
        s = item["scheme"]
        schemes_out.append({
            "scheme_id": s["scheme_id"],
            "name": s["name_en"],
            "benefit": s["benefit_amount"],
            "eligibility_match": item["match_reason"],
            "documents": s.get("documents_required", []),
            "apply_url": s.get("application_url", ""),
            "confidence": item["score"],
        })
    greet = VOICE_GREETINGS.get(lang, VOICE_GREETINGS["hi"])
    if schemes_out:
        names = ", ".join([x["name"] for x in schemes_out[:2]])
        if lang == "hi":
            voice = f"{greet}Aapke liye {len(schemes_out)} yojanayein mili hain. Sabse achhi: {names}. Details WhatsApp par bhej di hain."
        else:
            voice = f"{greet}I found {len(schemes_out)} schemes for you. Top match: {names}. Details sent below."
    else:
        voice = (f"{greet}Maaf kijiye, is jaankari par koi yojana nahi mili. Kripya apni umr, kaam aur gaon ke baare mein aur batayein."
                 if lang == "hi" else f"{greet}I couldn't find a scheme for this. Please tell me more about your age, work and location.")
    return {
        "language_detected": lang,
        "user_profile": profile,
        "schemes": schemes_out,
        "voice_response": voice,
    }
