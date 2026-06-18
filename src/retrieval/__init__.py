"""检索编排器 — ChromaDB 版本 (dense + sparse + RRF + rerank)"""
import logging
import time
from typing import List, Tuple
from chromadb import Collection

from src.retrieval.dense import dense_search
from src.retrieval.sparse import sparse_search
from src.retrieval.fusion import reciprocal_rank_fusion
from src.retrieval.reranker import rerank

logger = logging.getLogger(__name__)


def retrieve(
    query: str,
    collection: Collection,
    dense_top_k: int = 20,
    sparse_top_k: int = 20,
    fusion_top_k: int = 10,
    rerank_top_k: int = 5,
    enable_rerank: bool = True,
) -> Tuple[List[dict], dict]:
    """
    完整检索流水线
    Returns: (documents, timing_info)
    """
    timing = {}

    # Step 1: Dense retrieval (ChromaDB)
    t0 = time.time()
    dense_results = dense_search(query, collection, top_k=dense_top_k)
    timing["dense_ms"] = round((time.time() - t0) * 1000)

    # Step 2: Sparse retrieval (in-memory BM25)
    t0 = time.time()
    sparse_results = sparse_search(query, top_k=sparse_top_k)
    timing["sparse_ms"] = round((time.time() - t0) * 1000)

    # 拒绝判断
    if not dense_results and not sparse_results:
        return [], timing

    # Step 3: RRF Fusion
    t0 = time.time()
    fused = reciprocal_rank_fusion(
        dense_results, sparse_results, top_k=fusion_top_k,
    )
    timing["fusion_ms"] = round((time.time() - t0) * 1000)

    # Step 4: Re-rank
    if enable_rerank and len(fused) > rerank_top_k:
        t0 = time.time()
        fused = rerank(query, fused, top_k=rerank_top_k)
        timing["rerank_ms"] = round((time.time() - t0) * 1000)
    else:
        fused = fused[:rerank_top_k]
        timing["rerank_ms"] = 0

    if fused:
        timing["top_similarity"] = round(
            fused[0].get("rerank_score", fused[0].get("score", 0)), 4
        )

    return fused, timing
