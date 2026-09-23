"""Seed ChromaDB with scheme chunks. Safe to run repeatedly; skips if already populated."""
import json
import os
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "schemes_seed.json"


def scheme_to_text(s: dict) -> str:
    crit = s.get("eligibility_criteria", {})
    return (
        f"{s['scheme_id']} - {s['name_en']} ({s.get('name_hi', '')}). "
        f"Ministry: {s.get('ministry', '')}. State: {s.get('state', '')}. "
        f"Category: {', '.join(s.get('category', []))}. "
        f"Description: {s.get('description', '')} Benefit: {s.get('benefit_amount', '')}. "
        f"Eligibility: {json.dumps(crit)}. Documents: {', '.join(s.get('documents_required', []))}. "
        f"Apply: {s.get('application_url', '')}. Tags: {', '.join(s.get('tags', []))}"
    )


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        schemes = json.load(f)
    print(f"Loaded {len(schemes)} schemes")
    try:
        import chromadb
        from backend.config import CHROMA_PERSIST_DIR
    except ImportError:
        from config import CHROMA_PERSIST_DIR
        import chromadb
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    col = client.get_or_create_collection("indian_govt_schemes")
    if col.count() > 0:
        print(f"Collection already has {col.count()} docs, skipping.")
        return
    key = os.getenv("OPENAI_API_KEY", "")
    texts = [scheme_to_text(s) for s in schemes]
    ids = [s["scheme_id"] for s in schemes]
    metas = [{"scheme_id": s["scheme_id"], "category": ",".join(s.get("category", [])),
              "state": s.get("state", ""), "tags": ",".join(s.get("tags", []))} for s in schemes]
    if key:
        from openai import OpenAI
        client_oai = OpenAI(api_key=key)
        embs = []
        for i in range(0, len(texts), 50):
            batch = texts[i:i + 50]
            r = client_oai.embeddings.create(model="text-embedding-3-small", input=batch)
            embs.extend([d.embedding for d in r.data])
        col.add(ids=ids, documents=texts, metadatas=metas, embeddings=embs)
    else:
        col.add(ids=ids, documents=texts, metadatas=metas)
    print(f"Seeded {col.count()} docs.")


if __name__ == "__main__":
    main()
