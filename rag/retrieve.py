from sqlalchemy import text

def retrieve_context(db, query_vector, k=5):
    sql = """
    select id, content
    from rag_documents
    order by embedding <-> :vec
    limit :k
    """
    return db.execute(text(sql), {"vec": str(query_vector), "k": k}).fetchall()
