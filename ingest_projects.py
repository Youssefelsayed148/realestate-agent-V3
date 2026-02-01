import os
import re
from typing import List, Dict, Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text, bindparam
from sqlalchemy.orm import sessionmaker
from sentence_transformers import SentenceTransformer
from psycopg2.extras import Json  # ✅ IMPORTANT for jsonb

load_dotenv()

DATABASE_URL = os.getenv("SUPABASE_DB_URL")
if not DATABASE_URL:
    raise RuntimeError("Missing SUPABASE_DB_URL in .env")

EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
model = SentenceTransformer(EMBED_MODEL_NAME)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def clean_text(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()


def chunk_text(text_: str, max_chars: int = 900, overlap: int = 150) -> List[str]:
    text_ = clean_text(text_)
    if not text_:
        return []
    if len(text_) <= max_chars:
        return [text_]

    chunks: List[str] = []
    start = 0
    while start < len(text_):
        end = min(start + max_chars, len(text_))
        chunks.append(text_[start:end])
        if end == len(text_):
            break
        start = max(0, end - overlap)
    return chunks


def embed_texts(texts: List[str]) -> List[List[float]]:
    vecs = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vecs]


def fetch_projects(db) -> List[Dict[str, Any]]:
    q = text("""
        SELECT
          id, project_name, area, description,
          apartment_type_price, summary_path, html_summary
        FROM projects
        ORDER BY id
    """)
    return [dict(r) for r in db.execute(q).mappings().all()]


def delete_existing_project_docs(db, project_ids: List[int]) -> None:
    if not project_ids:
        return

    source_ids = [f"project:{pid}" for pid in project_ids]

    q = text("""
        DELETE FROM rag_documents
        WHERE source = 'projects'
          AND source_id IN :source_ids
    """).bindparams(bindparam("source_ids", expanding=True))

    db.execute(q, {"source_ids": source_ids})


def insert_docs(db, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return

    q = text("""
        INSERT INTO rag_documents (source, source_id, chunk_index, content, metadata, embedding)
        VALUES (:source, :source_id, :chunk_index, :content, :metadata, :embedding)
    """)
    db.execute(q, rows)


def build_project_text(p: Dict[str, Any]) -> str:
    name = clean_text(p.get("project_name") or "")
    area = clean_text(p.get("area") or "")
    desc = clean_text(p.get("description") or "")
    apt = clean_text(p.get("apartment_type_price") or "")
    html = clean_text(p.get("html_summary") or "")
    path = clean_text(p.get("summary_path") or "")

    parts = [f"Project: {name}."]
    if area:
        parts.append(f"Location/Area: {area}.")
    if desc:
        parts.append(f"Description: {desc}")
    if apt:
        parts.append(f"Apartment types & prices (raw): {apt}")
    if html:
        parts.append(f"HTML summary: {html}")
    if path:
        parts.append(f"Summary path: {path}")

    return " ".join(parts)


def main():
    db = SessionLocal()
    try:
        projects = fetch_projects(db)
        project_ids = [int(p["id"]) for p in projects]

        delete_existing_project_docs(db, project_ids)

        all_rows: List[Dict[str, Any]] = []

        for p in projects:
            pid = int(p["id"])
            content_full = build_project_text(p)
            chunks = chunk_text(content_full)
            if not chunks:
                continue

            vectors = embed_texts(chunks)

            meta = {
                "doc_type": "project",
                "project_id": pid,
                "project_name": clean_text(p.get("project_name") or ""),
                "location": clean_text(p.get("area") or "")
            }

            for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
                all_rows.append({
                    "source": "projects",
                    "source_id": f"project:{pid}",
                    "chunk_index": i,
                    "content": chunk,
                    "metadata": Json(meta),  # ✅ wrap dict for jsonb
                    "embedding": vec
                })

        insert_docs(db, all_rows)
        db.commit()
        print(f"✅ Inserted {len(all_rows)} project chunks into rag_documents (source='projects').")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
