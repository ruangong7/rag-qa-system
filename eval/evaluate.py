"""自动化评估 — 离线版 (不需 Qdrant/LLM)，在线版 (需服务运行)"""
import json
import time
import sys
from pathlib import Path
from typing import List, Dict, Set

from eval.metrics import (
    recall_at_k, precision_at_k, mrr, ndcg_at_k, hit_rate_at_k,
    compute_retrieval_report, faithfulness_score, context_precision,
)


def demo_retrieval_eval() -> Dict:
    """
    演示检索指标计算 (使用模拟数据验证公式正确性)
    实际运行时替换为真实的 retrieval result + annotation
    """
    # 模拟: 5 个查询，每个查询的检索结果和相关标注
    queries = ["年假制度", "数据泄露响应", "微服务架构", "密码策略", "备份恢复"]
    retrieved = [
        [1, 3, 5, 7, 9, 11, 13, 15, 17, 19],   # query 1 的结果
        [2, 4, 6, 8, 10, 1, 3, 5, 7, 9],        # query 2
        [3, 5, 1, 7, 9, 2, 4, 6, 8, 10],        # query 3
        [4, 2, 6, 1, 3, 5, 8, 7, 9, 10],        # query 4
        [5, 3, 1, 7, 2, 4, 6, 9, 8, 10],        # query 5
    ]
    relevant = [
        {1, 3, 5},     # query 1 的真正相关文档
        {2, 4},        # query 2
        {3, 5, 1},     # query 3
        {4, 2},        # query 4
        {5, 3, 1},     # query 5
    ]
    # 分级相关度 (0=不相关, 1=弱相关, 2=相关, 3=强相关)
    relevance_grades = [
        {1: 3, 3: 2, 5: 2, 7: 1, 9: 1},
        {2: 3, 4: 2, 6: 1, 8: 1},
        {3: 3, 5: 2, 1: 2, 7: 1},
        {4: 3, 2: 3, 6: 2, 1: 1},
        {5: 3, 3: 2, 1: 2, 7: 1},
    ]

    return compute_retrieval_report(queries, retrieved, relevant, relevance_grades)


def demo_generation_eval() -> Dict:
    """演示生成质量指标"""
    test_cases = [
        {
            "answer": "根据员工手册第3.1节，初级员工每年享有5天年假，中级10天，高级15天。",
            "contexts": [
                "初级员工（<3年）：每年5个工作日。中级员工（3-10年）：每年10个工作日。高级员工（>10年）：每年15个工作日。",
                "年假可顺延至下一日历年，最多5天。",
            ],
            "relevant_snippets": ["初级员工每年5天年假", "中级10天", "高级15天"],
            "expected_label": "factual",
        },
        {
            "answer": "数据泄露发生后必须在72小时内通知监管机构，并在1小时内召集DBRT。",
            "contexts": [
                "Notification: Notify the supervisory authority within 72 hours of becoming aware of the breach.",
                "Data Breach Response Team (DBRT) must be convened within 1 hour of breach detection.",
            ],
            "relevant_snippets": ["72小时内通知", "1小时内召集DBRT"],
            "expected_label": "factual",
        },
        {
            "answer": "公司建议员工使用复杂的密码并定期更换，以提高安全性。",
            "contexts": [
                "Password Policy: Minimum 12 characters, must include uppercase, lowercase, digit, and special character. Rotation every 90 days.",
            ],
            "relevant_snippets": ["密码最少12字符", "包含大小写数字特殊字符", "90天更换"],
            "expected_label": "partial_hallucination",  # 答案说"建议使用复杂密码"但原文是强制要求
        },
    ]

    results = []
    total_faith = 0
    total_cp = 0

    for tc in test_cases:
        faith = faithfulness_score(tc["answer"], tc["contexts"])
        cp = context_precision(tc["contexts"], tc["relevant_snippets"])
        total_faith += faith
        total_cp += cp
        results.append({
            "label": tc["expected_label"],
            "faithfulness": round(faith, 3),
            "context_precision": round(cp, 3),
        })

    n = len(test_cases)
    return {
        "avg_faithfulness": round(total_faith / n, 3),
        "avg_context_precision": round(total_cp / n, 3),
        "details": results,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("📊 RAG QA System — 离线评估报告")
    print("=" * 60)

    print("\n─── 1. 检索质量 (Retrieval Metrics) ───")
    retrieval_report = demo_retrieval_eval()
    for metric, value in retrieval_report.items():
        print(f"  {metric:20s}: {value}")

    print("\n─── 2. 生成质量 (Generation Metrics) ───")
    gen_report = demo_generation_eval()
    print(f"  平均忠实度 (Faithfulness)    : {gen_report['avg_faithfulness']}")
    print(f"  平均上下文精度 (Context Prec) : {gen_report['avg_context_precision']}")
    for d in gen_report["details"]:
        print(f"    [{d['label']}] faith={d['faithfulness']}, cp={d['context_precision']}")

    print("\n─── 3. 系统延迟预算 ───")
    latency_budget = {
        "query_rewrite": "≤ 500ms",
        "safety_check": "≤ 5ms",
        "dense_retrieval": "≤ 50ms",
        "sparse_retrieval": "≤ 20ms",
        "rrf_fusion": "≤ 2ms",
        "rerank": "≤ 300ms",
        "generation": "≤ 3000ms",
        "postprocess": "≤ 10ms",
        "total_budget": "~4s (余量6s, 目标 ≤ 10s P90)",
    }
    for stage, budget in latency_budget.items():
        print(f"  {stage:25s}: {budget}")

    print("\n⚠️  注意: 延迟数据为设计预算，实际值需运行在线评估获取。")
    print("    在线评估: python3 eval/evaluate.py (需 Qdrant + LLM API)")
