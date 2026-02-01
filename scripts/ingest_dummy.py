from sqlalchemy import text
from db import get_db

def main():
    db = get_db()
    try:
        db.execute(
            text("""
                insert into rag_documents (source, source_id, chunk_index, content, metadata)
                values (:source, :source_id, :chunk_index, :content, :metadata::jsonb)
            """),
            {
                "source": "projects",
                "source_id": "dummy_project_1",
                "chunk_index": 0,
                "content": "Project Dummy is located in New Cairo. Prices start from 5,000,000 EGP.",
                "metadata": '{"type":"dummy"}',
            }
        )
        db.commit()
        print("✅ Inserted 1 dummy row into rag_documents")
    finally:
        db.close()

if __name__ == "__main__":
    main()
