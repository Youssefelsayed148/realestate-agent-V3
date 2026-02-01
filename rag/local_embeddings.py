from sentence_transformers import SentenceTransformer

# Small, fast, excellent for RAG
_MODEL_NAME = "all-MiniLM-L6-v2"  # 384 dimensions

_model = SentenceTransformer(_MODEL_NAME)

def embed_texts(texts: list[str]) -> list[list[float]]:
    embeddings = _model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False
    )
    return embeddings.tolist()
