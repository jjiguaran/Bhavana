# services/meditation_cache.py

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from sentence_transformers import SentenceTransformer
import uuid
import random

COLLECTION_NAME = "meditation_dynamic_cache"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
embedding_model = SentenceTransformer(EMBEDDING_MODEL)
qdrant = QdrantClient(host="localhost", port=6333)

def ensure_collection():
    qdrant.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=rest.VectorParams(size=384, distance=rest.Distance.COSINE)
    )

def store_in_cache(query, response_text, level, duration):
    vector = embedding_model.encode(query).tolist()
    metadata = {
        "query": query,
        "response": response_text,
        "level": level,
        "duration": duration,
    }
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            rest.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload=metadata
            )
        ]
    )

def search_cache(query, level, duration, top_k=5, threshold=0.9):
    vector = embedding_model.encode(query).tolist()
    results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=vector,
        limit=top_k,
        with_payload=True
    )
    return [
        r.payload for r in results
        if r.score > threshold and
           r.payload["level"] == level and
           r.payload["duration"] == duration
    ]

def get_or_generate_text(query, level, duration, generate_fn):
    hits = search_cache(query, level, duration)
    if hits:
        return random.choice(hits)["response"]
    new_text = generate_fn()
    store_in_cache(query, new_text, level, duration)
    return new_text
