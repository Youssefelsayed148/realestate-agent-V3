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
    """Convert anything (including None) to a normalized single-line string."""
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
        # Handles Decimal, int, float, numeric strings
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
    except (TypeError, ValueError):
        return None


def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    vecs = model.encode(list(texts), normalize_embeddings=True)
    return [v.tolist() for v in vecs]


def fetch_units_with_project(db) -> List[Dict[str, Any]]:
    # Join projects so content includes project_name + area (location)
    q = text(
        """
        SELECT
          u.id,
          u.project_id,
          u.unit_number,
          u.unit_type,
          u.bedrooms,
          u.bathrooms,
          u.area_sqm,
          u.view,
          u.price,
          u.currency,
          u.floor,
          u.building,
          u.status,
          u.project_unit_type_id,
          p.project_name,
          p.area AS project_area
        FROM public.units u
        JOIN public.projects p ON p.id = u.project_id
        ORDER BY u.id
        """
    )
    return [dict(r) for r in db.execute(q).mappings().all()]


def delete_existing_unit_docs(db, unit_ids: Sequence[int]) -> None:
    if not unit_ids:
        return

    source_ids = [f"unit:{uid}" for uid in unit_ids]

    q = (
        text(
            """
            DELETE FROM public.rag_documents
            WHERE source = 'units'
              AND source_id IN :source_ids
            """
        )
        .bindparams(bindparam("source_ids", expanding=True))
    )

    db.execute(q, {"source_ids": source_ids})


def insert_docs(db, rows: Sequence[Dict[str, Any]]) -> None:
    if not rows:
        return
    q = text(
        """
        INSERT INTO public.rag_documents (source, source_id, chunk_index, content, metadata, embedding)
        VALUES (:source, :source_id, :chunk_index, :content, :metadata, :embedding)
        """
    )
    db.execute(q, list(rows))


def build_unit_text(u: Dict[str, Any]) -> str:
    project_name = clean_text(u.get("project_name"))
    project_area = clean_text(u.get("project_area"))

    unit_type = clean_text(u.get("unit_type"))
    unit_number = clean_text(u.get("unit_number"))
    view = clean_text(u.get("view"))
    building = clean_text(u.get("building"))
    status = clean_text(u.get("status"))

    bedrooms = to_int(u.get("bedrooms"))
    bathrooms = to_int(u.get("bathrooms"))
    area_sqm = to_float(u.get("area_sqm"))
    price = u.get("price")  # keep raw for display; may be Decimal
    currency = clean_text(u.get("currency"))
    floor = to_int(u.get("floor"))

    parts: List[str] = [f"Unit in project {project_name}."]
    if project_area:
        parts.append(f"Location/Area: {project_area}.")
    if unit_type:
        parts.append(f"Unit type: {unit_type}.")
    if unit_number:
        parts.append(f"Unit number: {unit_number}.")
    if bedrooms is not None:
        parts.append(f"Bedrooms: {bedrooms}.")
    if bathrooms is not None:
        parts.append(f"Bathrooms: {bathrooms}.")
    if area_sqm is not None:
        parts.append(f"Area: {area_sqm:g} sqm.")
    if view:
        parts.append(f"View: {view}.")
    if floor is not None:
        parts.append(f"Floor: {floor}.")
    if building:
        parts.append(f"Building: {building}.")
    if price is not None:
        parts.append(f"Price: {price} {currency}".strip() + ".")
    if status:
        parts.append(f"Status: {status}.")

    return " ".join(parts)


def main() -> None:
    db = SessionLocal()
    try:
        units = fetch_units_with_project(db)
        unit_ids = [to_int(u.get("id")) for u in units]
        unit_ids_clean = [uid for uid in unit_ids if uid is not None]

        delete_existing_unit_docs(db, unit_ids_clean)

        texts: List[str] = []
        rows_payload: List[Dict[str, Any]] = []

        for u in units:
            uid = to_int(u.get("id"))
            pid = to_int(u.get("project_id"))
            if uid is None or pid is None:
                continue  # skip broken rows safely

            content = build_unit_text(u)

            meta: Dict[str, Any] = {
                "doc_type": "unit",
                "unit_id": uid,
                "project_id": pid,
                "project_name": clean_text(u.get("project_name")),
                "location": clean_text(u.get("project_area")),
                "unit_type": clean_text(u.get("unit_type")),
                "unit_number": clean_text(u.get("unit_number")),
                "bedrooms": to_int(u.get("bedrooms")),
                "bathrooms": to_int(u.get("bathrooms")),
                "area_sqm": to_float(u.get("area_sqm")),
                "view": clean_text(u.get("view")) or None,
                "price": to_float(u.get("price")),
                "currency": clean_text(u.get("currency")) or None,
                "floor": to_int(u.get("floor")),
                "building": clean_text(u.get("building")) or None,
                "status": clean_text(u.get("status")) or None,
                "project_unit_type_id": to_int(u.get("project_unit_type_id")),
            }

            texts.append(content)
            rows_payload.append(
                {
                    "source": "units",
                    "source_id": f"unit:{uid}",
                    "chunk_index": 0,
                    "content": content,
                    "metadata": Json(meta),  # ✅ jsonb adaptation
                    "embedding": None,       # set after embeddings computed
                }
            )

        if not rows_payload:
            print("⚠️ No units found to ingest.")
            db.commit()
            return

        vectors = embed_texts(texts)
        if len(vectors) != len(rows_payload):
            raise RuntimeError("Embedding count mismatch with rows payload.")

        for row, vec in zip(rows_payload, vectors):
            row["embedding"] = vec

        insert_docs(db, rows_payload)
        db.commit()
        print(f"✅ Inserted {len(rows_payload)} unit docs into rag_documents (source='units').")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
