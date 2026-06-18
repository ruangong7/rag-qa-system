"""Dense retrieval - BGE-M3 + ChromaDB"""
import logging
from typing import List
from chromadb import Collection

logger = logging.getLogger(__name__)

_embedding_model = None


def _get_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("BAAI/bge-m3")
    return _embedding_model


def dense_search(
    query: str,
    collection: Collection,
    top_k: int = 20,
) -> List[dict]:
    """Dense 向量检索 via ChromaDB"""
    model = _get_model()
    query_embedding = model.encode(
        query, normalize_embeddings=True
    ).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs = []
    if results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i] if results["distances"] else 0.0
            # ChromaDB cosine distance → convert to similarity score
            score = 1.0 - distance  # cosine similarity = 1 - cosine distance

            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            docs.append({
                "id": doc_id,
                "text": results["documents"][0][i] if results["documents"] else "",
                "score": round(score, 4),
                "source_file": metadata.get("source_file", ""),
                "page_number": metadata.get("page_number", 1),
            })

    # Filter by threshold (cosine similarity > 0.4)
    docs = [d for d in docs if d["score"] > 0.4]
    return docs
