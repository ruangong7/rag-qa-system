"""评估指标计算模块 — 不依赖外部API, 纯离线计算"""
from typing import List, Dict, Set
import math


def recall_at_k(
    retrieved_ids: List[int],
    relevant_ids: Set[int],
    k: int,
) -> float:
    """Recall@k: 检索到的相关文档数 / 总相关文档数"""
    if not relevant_ids:
        return 0.0
    retrieved_at_k = set(retrieved_ids[:k])
    hits = retrieved_at_k & relevant_ids
    return len(hits) / len(relevant_ids)


def precision_at_k(
    retrieved_ids: List[int],
    relevant_ids: Set[int],
    k: int,
) -> float:
    """Precision@k: 前k个结果中相关文档的比例"""
    if k == 0:
        return 0.0
    retrieved_at_k = retrieved_ids[:k]
    if not retrieved_at_k:
        return 0.0
    hits = set(retrieved_at_k) & relevant_ids
    return len(hits) / k


def mrr(retrieved_ids_list: List[List[int]], relevant_ids_list: List[Set[int]]) -> float:
    """Mean Reciprocal Rank: 第一个相关文档排名的倒数均值"""
    if not retrieved_ids_list:
        return 0.0
    total = 0.0
    for retrieved_ids, relevant_ids in zip(retrieved_ids_list, relevant_ids_list):
        for rank, doc_id in enumerate(retrieved_ids, start=1):
            if doc_id in relevant_ids:
                total += 1.0 / rank
                break
    return total / len(retrieved_ids_list)


def ndcg_at_k(
    retrieved_ids: List[int],
    relevance_scores: Dict[int, int],
    k: int,
) -> float:
    """NDCG@k: 考虑排序位置和相关性等级的归一化折损累计增益"""
    if k == 0 or not relevance_scores:
        return 0.0

    # DCG
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_ids[:k]):
        rel = relevance_scores.get(doc_id, 0)
        dcg += rel / math.log2(i + 2)  # i+2 because log₂(1)=0

    # IDCG (ideal DCG) — sort relevance scores descending
    ideal_rels = sorted(relevance_scores.values(), reverse=True)[:k]
    idcg = 0.0
    for i, rel in enumerate(ideal_rels):
        idcg += rel / math.log2(i + 2)

    if idcg == 0:
        return 0.0
    return dcg / idcg


def hit_rate_at_k(
    retrieved_ids_list: List[List[int]],
    relevant_ids_list: List[Set[int]],
    k: int,
) -> float:
    """Hit Rate@k: 至少命中一个相关文档的查询比例"""
    if not retrieved_ids_list:
        return 0.0
    hits = 0
    for retrieved_ids, relevant_ids in zip(retrieved_ids_list, relevant_ids_list):
        if set(retrieved_ids[:k]) & relevant_ids:
            hits += 1
    return hits / len(retrieved_ids_list)


def faithfulness_score(
    answer: str,
    context_texts: List[str],
) -> float:
    """
    忠实度：答案中可追溯到检索内容的句子的比例。
    简化实现：检查答案句子是否与任一 context 有足够的 n-gram 重叠。
    """
    import re
    sentences = re.split(r'[。！？.!?\n]', answer)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    if not sentences:
        return 0.0

    grounded = 0
    for sent in sentences:
        chars = set(sent)
        for ctx in context_texts:
            overlap = len(chars & set(ctx)) / len(chars)
            if overlap > 0.5:  # 50% 字符有来源
                grounded += 1
                break

    return grounded / len(sentences)


def context_precision(
    retrieved_texts: List[str],
    relevant_snippets: List[str],
) -> float:
    """
    上下文精度：检索结果中确实与答案相关的 chunk 比例。
    用最大公共子串比率判断相关性。
    """
    if not retrieved_texts:
        return 0.0
    relevant = 0
    for rt in retrieved_texts:
        for rs in relevant_snippets:
            if _lcs_ratio(rt, rs) > 0.3:
                relevant += 1
                break
    return relevant / len(retrieved_texts)


def _lcs_ratio(a: str, b: str) -> float:
    """简化的最长公共子串比率 (基于字符集)"""
    if not a or not b:
        return 0.0
    set_a = set(a)
    set_b = set(b)
    return len(set_a & set_b) / min(len(set_a), len(set_b))


# ─── 综合评估报告 ───

def compute_retrieval_report(
    queries: List[str],
    retrieved_results: List[List[int]],     # 每个 query 的检索结果 doc_id 列表
    relevance_annotations: List[Set[int]], # 每个 query 的相关 doc_id 集合
    relevance_scores: List[Dict[int, int]] = None,  # 分级相关度 (0-3)
) -> Dict:
    """计算检索质量全指标"""
    k_values = [1, 3, 5, 10]
    report = {}

    for k in k_values:
        recall = sum(
            recall_at_k(r, rel, k)
            for r, rel in zip(retrieved_results, relevance_annotations)
        ) / len(queries)

        precision = sum(
            precision_at_k(r, rel, k)
            for r, rel in zip(retrieved_results, relevance_annotations)
        ) / len(queries)

        hit = hit_rate_at_k(retrieved_results, relevance_annotations, k)

        report[f"Recall@{k}"] = round(recall, 4)
        report[f"Precision@{k}"] = round(precision, 4)
        report[f"HitRate@{k}"] = round(hit, 4)

    report["MRR"] = round(mrr(retrieved_results, relevance_annotations), 4)

    if relevance_scores:
        ndcg_scores = []
        for r, rel_scores in zip(retrieved_results, relevance_scores):
            ndcg_scores.append(ndcg_at_k(r, rel_scores, k=10))
        report["NDCG@10"] = round(sum(ndcg_scores) / len(ndcg_scores), 4)

    return report
