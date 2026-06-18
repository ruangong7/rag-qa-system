"""
索引器 - BGE-M3 embedding + ChromaDB 入库 (纯 Python, 无需 Docker)
"""
import logging
from pathlib import Path
from typing import List
import chromadb
from chromadb.config import Settings

from src.ingestion.loader import load_all_documents

logger = logging.getLogger(__name__)

COLLECTION_NAME = "rag_docs"


def get_embedding_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("BAAI/bge-m3")


def build_index(data_dir: str, persist_dir: str = "./chroma_data"):
    """完整索引构建流程 — ChromaDB 版本"""
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(anonymized_telemetry=False),
    )

    # 删旧建新
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # 加载文档
    chunks = load_all_documents(Path(data_dir))
    if not chunks:
        logger.warning("no documents found in %s", data_dir)
        return 0

    # 生成 embedding
    model = get_embedding_model()
    texts = [c["text"] for c in chunks]
    logger.info("generating embeddings for %d chunks (CPU)", len(texts))

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    # 入库
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i + batch_size]
        batch_embs = embeddings[i:i + batch_size]

        collection.add(
            ids=[str(i + j) for j in range(len(batch_chunks))],
            embeddings=batch_embs.tolist(),
            metadatas=[
                {
                    "source_file": c["metadata"]["source_file"],
                    "page_number": c["metadata"]["page_number"],
                    "doc_type": c["metadata"]["doc_type"],
                    "chunk_hash": c["metadata"]["chunk_hash"],
                }
                for c in batch_chunks
            ],
            documents=[c["text"] for c in batch_chunks],
        )

    logger.info("index built: %d points in %s", len(chunks), persist_dir)
    return len(chunks)


def get_collection(persist_dir: str = "./chroma_data"):
    """获取 ChromaDB collection"""
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_collection(COLLECTION_NAME)
