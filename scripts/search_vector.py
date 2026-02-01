from sqlalchemy import text
from db import get_db
from rag.local_embeddings import embed_texts

def main():
    db = get_db()
    try:
        query = "projects in New Cairo"
        qvec = embed_texts([query])[0]
        qvec_str = str(qvec)

        rows = db.execute(
            text("""
                select id, source, source_id, chunk_index, content,
                       (embedding <-> CAST(:qvec AS vector)) as distance
                from rag_documents
                where embedding is not null
                order by embedding <-> CAST(:qvec AS vector)
                limit 5
            """),
            {"qvec": qvec_str}
        ).mappings().all()

        print(f"✅ Top matches for: {query}")
        for r in rows:
            print("-" * 70)
            print(
                f"distance={float(r['distance']):.4f} | source={r['source']} | source_id={r['source_id']} | chunk={r['chunk_index']}"
            )
            print(r["content"])
    finally:
        db.close()

if __name__ == "__main__":
    main()
