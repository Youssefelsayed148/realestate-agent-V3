from sqlalchemy import text
from db import get_db

def main():
    db = get_db()
    try:
        rows = db.execute(
            text("""
                select id, source, source_id, chunk_index, content
                from rag_documents
                order by id desc
                limit 5
            """)
        ).mappings().all()

        print(f"✅ Retrieved {len(rows)} rows")
        for r in rows:
            print("-" * 60)
            print(f"id={r['id']} source={r['source']} source_id={r['source_id']} chunk={r['chunk_index']}")
            print(r["content"])
    finally:
        db.close()

if __name__ == "__main__":
    main()
