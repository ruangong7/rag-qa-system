"""Retrieval orchestrator: dense + sparse + RRF + optional rerank."""
import logging
import time
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from chromadb import Collection
else:
    Collection = object

logger = logging.getLogger(__name__)


def retrieve(
    query: str,
    collection: Collection,
    dense_top_k: int = 20,
    sparse_top_k: int = 20,
    fusion_top_k: int = 10,
    rerank_top_k: int = 3,
    enable_rerank: bool = True,
) -> Tuple[List[dict], dict]:
    from src.retrieval.dense import dense_search
    from src.retrieval.fusion import reciprocal_rank_fusion
    from src.retrieval.reranker import rerank
    from src.retrieval.sparse import sparse_search

    timing = {}

    t0 = time.time()
    dense_results = dense_search(query, collection, top_k=dense_top_k)
    timing["dense_ms"] = round((time.time() - t0) * 1000)
    timing["dense_top_similarity"] = round(float(dense_results[0].get("score", 0.0)), 4) if dense_results else 0.0

    t0 = time.time()
    sparse_results = sparse_search(query, top_k=sparse_top_k)
    timing["sparse_ms"] = round((time.time() - t0) * 1000)

    if not dense_results and not sparse_results:
        return [], timing

    t0 = time.time()
    fused = reciprocal_rank_fusion(dense_results, sparse_results, top_k=max(fusion_top_k, rerank_top_k))
    timing["fusion_ms"] = round((time.time() - t0) * 1000)

    if enable_rerank and len(fused) > rerank_top_k:
        t0 = time.time()
        try:
            fused = rerank(query, fused, top_k=rerank_top_k)
        except Exception as exc:
            logger.warning("rerank failed, falling back to RRF order: %s", exc)
            fused = fused[:rerank_top_k]
        timing["rerank_ms"] = round((time.time() - t0) * 1000)
    else:
        fused = fused[:rerank_top_k]
        timing["rerank_ms"] = 0

    if fused:
        if "rerank_score" in fused[0]:
            timing["top_score_type"] = "rerank_score"
            timing["top_similarity"] = round(float(fused[0].get("rerank_score", 0.0)), 4)
        elif "rrf_score" in fused[0]:
            timing["top_score_type"] = "rrf_score"
            timing["top_similarity"] = round(float(fused[0].get("rrf_score", 0.0)), 4)
        else:
            timing["top_score_type"] = "dense_or_sparse_score"
            timing["top_similarity"] = round(float(fused[0].get("score", 0.0)), 4)

    return fused, timing
