"""Re-ranker - BGE-Reranker-v2-m3."""
import logging
import os
from typing import List

logger = logging.getLogger(__name__)

_reranker = None


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _get_reranker():
    global _reranker
    if _reranker is None:
        from FlagEmbedding import FlagReranker

        model_name = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
        device = os.getenv("RERANKER_DEVICE", "cpu").lower()
        use_fp16 = _env_bool("RERANKER_USE_FP16", device.startswith("cuda"))
        local_files_only = os.getenv("HF_HUB_OFFLINE") == "1" or os.getenv("TRANSFORMERS_OFFLINE") == "1"
        if device == "cpu":
            use_fp16 = False

        logger.info(
            "Loading reranker model=%s device=%s use_fp16=%s local_files_only=%s",
            model_name,
            device,
            use_fp16,
            local_files_only,
        )
        _reranker = FlagReranker(
            model_name,
            use_fp16=use_fp16,
            local_files_only=local_files_only,
        )
    return _reranker


def rerank(
    query: str,
    candidates: List[dict],
    top_k: int = 5,
) -> List[dict]:
    """Cross-encoder rerank."""
    if not candidates:
        return []

    reranker = _get_reranker()
    pairs = [[query, c["text"]] for c in candidates]
    scores = reranker.compute_score(pairs, normalize=True)

    for item, score in zip(candidates, scores):
        item["rerank_score"] = round(float(score), 4)

    candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
    return candidates[:top_k]
