"""
Reciprocal Rank Fusion (RRF) - 融合 dense & sparse 结果
"""
from typing import List


def reciprocal_rank_fusion(
    dense_results: List[dict],
    sparse_results: List[dict],
    k: int = 60,
    top_k: int = 10,
) -> List[dict]:
    """
    RRF 融合两个排序列表
    score = sum(1/(k + rank_i)) for each list containing the doc
    """
    scores = {}  # id -> {score, data}

    for rank, item in enumerate(dense_results, start=1):
        doc_id = item["id"]
        rrf_score = 1.0 / (k + rank)
        if doc_id in scores:
            scores[doc_id]["score"] += rrf_score
        else:
            scores[doc_id] = {"score": rrf_score, "data": item}

    for rank, item in enumerate(sparse_results, start=1):
        doc_id = item["id"]
        rrf_score = 1.0 / (k + rank)
        if doc_id in scores:
            scores[doc_id]["score"] += rrf_score
        else:
            scores[doc_id] = {"score": rrf_score, "data": item}

    # 按 RRF 分数排序
    sorted_items = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
    result = []
    for item in sorted_items[:top_k]:
        entry = item["data"].copy()
        entry["rrf_score"] = round(item["score"], 4)
        result.append(entry)

    return result
