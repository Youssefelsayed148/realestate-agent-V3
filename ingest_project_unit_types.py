import os
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from dotenv import load_dotenv
from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.orm import sessionmaker
from sentence_transformers import SentenceTransformer
from psycopg2.extras import Json

load_dotenv()

DATABASE_URL = os.getenv("SUPABASE_DB_URL")
if not DATABASE_URL:
    raise RuntimeError("Missing SUPABASE_DB_URL in .env")

EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
model = SentenceTransformer(EMBED_MODEL_NAME)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
    except (TypeError, ValueError):
        return None


def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    vecs = model.encode(list(texts), normalize_embeddings=True)
    return [v.tolist() for v in vecs]


def fetch_put_with_project(db) -> List[Dict[str, Any]]:
    # Join projects so docs include project_name + location(area)
    q = text("""
        SELECT
          put.id AS put_id,
          put.project_id,
          put.unit_type,
          put.area AS unit_area_sqm,
          put.price AS unit_price,
          p.project_name,
          p.area AS project_area
        FROM public.project_unit_types put
        JOIN public.projects p ON p.id = put.project_id
        ORDER BY put.project_id, put.id
    """)
    return [dict(r) for r in db.execute(q).mappings().all()]


def delete_existing_put_docs(db, put_ids: Sequence[int]) -> None:
    if not put_ids:
        return

    source_ids = [f"put:{pid}" for pid in put_ids]

    q = text("""
        DELETE FROM public.rag_documents
        WHERE source = 'project_unit_types'
          AND source_id IN :source_ids
    """).bindparams(bindparam("source_ids", expanding=True))

    db.execute(q, {"source_ids": source_ids})


def insert_docs(db, rows: Sequence[Dict[str, Any]]) -> None:
    if not rows:
        return

    q = text("""
        INSERT INTO public.rag_documents (source, source_id, chunk_index, content, metadata, embedding)
        VALUES (:source, :source_id, :chunk_index, :content, :metadata, :embedding)
    """)
    db.execute(q, list(rows))


def build_put_text(row: Dict[str, Any]) -> str:
    project_name = clean_text(row.get("project_name"))
    project_area = clean_text(row.get("project_area"))
    unit_type = clean_text(row.get("unit_type"))

    area_sqm = to_float(row.get("unit_area_sqm"))
    price = row.get("unit_price")  # keep raw for display; may be Decimal

    parts: List[str] = [f"Unit type option in project {project_name}."]
    if project_area:
        parts.append(f"Location/Area: {project_area}.")
    if unit_type:
        parts.append(f"Unit type: {unit_type}.")
    if area_sqm is not None:
        parts.append(f"Area: {area_sqm:g} sqm.")
    if price is not None:
        parts.append(f"Price: {price} EGP.")

    return " ".join(parts)


def main() -> None:
    db = SessionLocal()
    try:
        rows = fetch_put_with_project(db)

        put_ids = [to_int(r.get("put_id")) for r in rows]
        put_ids_clean = [x for x in put_ids if x is not None]

        # idempotent refresh
        delete_existing_put_docs(db, put_ids_clean)

        texts: List[str] = []
        payload: List[Dict[str, Any]] = []

        for r in rows:
            put_id = to_int(r.get("put_id"))
            project_id = to_int(r.get("project_id"))
            if put_id is None or project_id is None:
                continue

            content = build_put_text(r)

            meta: Dict[str, Any] = {
                "doc_type": "project_unit_type",
                "put_id": put_id,
                "project_id": project_id,
                "project_name": clean_text(r.get("project_name")),
                "location": clean_text(r.get("project_area")),
                "unit_type": clean_text(r.get("unit_type")),
                "area_sqm": to_float(r.get("unit_area_sqm")),
                "price_egp": to_float(r.get("unit_price")),
            }

            texts.append(content)
            payload.append({
                "source": "project_unit_types",
                "source_id": f"put:{put_id}",
                "chunk_index": 0,
                "content": content,
                "metadata": Json(meta),
                "embedding": None,  # set after embedding
            })

        if not payload:
            print("⚠️ No project_unit_types rows to ingest.")
            db.commit()
            return

        vectors = embed_texts(texts)
        if len(vectors) != len(payload):
            raise RuntimeError("Embedding count mismatch with payload.")

        for row, vec in zip(payload, vectors):
            row["embedding"] = vec

        insert_docs(db, payload)
        db.commit()
        print(f"✅ Inserted {len(payload)} project_unit_types docs into rag_documents (source='project_unit_types').")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
