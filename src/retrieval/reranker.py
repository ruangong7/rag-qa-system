"""Re-ranker - BGE-Reranker-v2-m3 精排"""
import logging
from typing import List

logger = logging.getLogger(__name__)

_reranker = None


def _get_reranker():
    global _reranker
    if _reranker is None:
        from FlagEmbedding import FlagReranker
        _reranker = FlagReranker(
            "BAAI/bge-reranker-v2-m3",
            use_fp16=True,
        )
    return _reranker


def rerank(
    query: str,
    candidates: List[dict],
    top_k: int = 5,
) -> List[dict]:
    """Cross-encoder 精排"""
    if not candidates:
        return []

    reranker = _get_reranker()
    pairs = [[query, c["text"]] for c in candidates]
    scores = reranker.compute_score(pairs, normalize=True)

    # 附加 rerank 分数
    for item, score in zip(candidates, scores):
        item["rerank_score"] = round(float(score), 4)

    # 按 rerank 分数降序
    candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

    return candidates[:top_k]
