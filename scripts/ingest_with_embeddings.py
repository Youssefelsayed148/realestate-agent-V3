from sqlalchemy import text
from db import get_db
from rag.local_embeddings import embed_texts
from psycopg2.extras import Json

def main():
    db = get_db()
    try:
        content = "Project Dummy is located in New Cairo. Prices start from 5,000,000 EGP."
        vec = embed_texts([content])[0]

        db.execute(
            text("""
                insert into rag_documents
                (source, source_id, chunk_index, content, metadata, embedding)
                values (:source, :source_id, :chunk_index, :content, :metadata, CAST(:embedding AS vector))
            """),
            {
                "source": "projects",
                "source_id": "dummy_project_vec_1",
                "chunk_index": 0,
                "content": content,
                "metadata": Json({"type": "dummy", "embedded": True}),  # ✅ wrap dict
                "embedding": str(vec),
            }
        )
        db.commit()
        print("✅ Inserted 1 embedded row into rag_documents")
    finally:
        db.close()

if __name__ == "__main__":
    main()
