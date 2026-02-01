from openai import OpenAI

client = OpenAI()

def embed_texts(texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
    # encoding_format="float" returns raw floats (what we want for pgvector)
    resp = client.embeddings.create(
        model=model,
        input=texts,
        encoding_format="float",
    )
    return [item.embedding for item in resp.data]
