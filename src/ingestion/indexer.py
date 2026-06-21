"""Indexer: ChromaDB + SentenceTransformer embedding + BM25 persistence."""
import logging
import os
from pathlib import Path

import chromadb
from chromadb.config import Settings

from src.ingestion.loader import load_all_documents
from src.retrieval.sparse import build_bm25_index, save_bm25_index

logger = logging.getLogger(__name__)
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

COLLECTION_NAME = "rag_docs"


def get_embedding_model():
    from sentence_transformers import SentenceTransformer

    model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    local_files_only = os.getenv("HF_HUB_OFFLINE") == "1" or os.getenv("TRANSFORMERS_OFFLINE") == "1"
    device = os.getenv("EMBEDDING_DEVICE", "cpu")
    return SentenceTransformer(model_name, local_files_only=local_files_only, device=device)


def build_index(data_dir: str, persist_dir: str = "./chroma_data"):
    client = chromadb.PersistentClient(path=persist_dir, settings=Settings(anonymized_telemetry=False))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    chunks = load_all_documents(Path(data_dir))
    if not chunks:
        logger.warning("no documents found in %s", data_dir)
        return 0

    bm25_path = Path(persist_dir) / "bm25.pkl"
    build_bm25_index(chunks)

    model = get_embedding_model()
    texts = [c["text"] for c in chunks]
    batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "2"))
    logger.info("generating embeddings for %d chunks", len(texts))

    embedding_batches = []
    for start in range(0, len(texts), batch_size):
        end = min(start + batch_size, len(texts))
        logger.info("embedding batch %d-%d/%d", start + 1, end, len(texts))
        embedding_batches.append(
            model.encode(
                texts[start:end],
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=batch_size,
            )
        )

    import numpy as np

    embeddings = np.vstack(embedding_batches)
    write_batch_size = 100
    for i in range(0, len(chunks), write_batch_size):
        batch_chunks = chunks[i : i + write_batch_size]
        batch_embs = embeddings[i : i + write_batch_size]
        collection.add(
            ids=[str(i + j) for j in range(len(batch_chunks))],
            embeddings=batch_embs.tolist(),
            metadatas=[
                {
                    "source_file": c["metadata"]["source_file"],
                    "page_number": c["metadata"]["page_number"],
                    "section": c["metadata"].get("section", ""),
                    "section_path": c["metadata"].get("section_path", ""),
                    "doc_title": c["metadata"].get("doc_title", ""),
                    "department": c["metadata"].get("department", "General"),
                    "doc_type": c["metadata"]["doc_type"],
                    "chunk_hash": c["metadata"]["chunk_hash"],
                }
                for c in batch_chunks
            ],
            documents=[c["text"] for c in batch_chunks],
        )

    save_bm25_index(str(bm25_path))
    logger.info("index built: %d points in %s", len(chunks), persist_dir)
    return len(chunks)


def get_collection(persist_dir: str = "./chroma_data"):
    client = chromadb.PersistentClient(path=persist_dir, settings=Settings(anonymized_telemetry=False))
    return client.get_collection(COLLECTION_NAME)
