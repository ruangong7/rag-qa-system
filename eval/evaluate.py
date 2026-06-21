"""Online evaluation runner against /chat using golden source-file matching."""
import json
import sys
import time
from pathlib import Path

import requests


def _load_eval_set() -> list[dict]:
    return json.loads(Path("eval/eval_set.json").read_text(encoding="utf-8"))


def _ordered_unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _latency_percentile(latencies: list[float], p: float) -> float:
    if not latencies:
        return 0
    ordered = sorted(latencies)
    idx = min(len(ordered) - 1, int(len(ordered) * p))
    return ordered[idx]


def _evaluate_case(case: dict, data: dict) -> dict:
    citations = data.get("citations", [])
    contexts = data.get("retrieved_contexts", [])
    confidence = data.get("confidence", 0.0)
    expect_rejection = case.get("expect_rejection", False)
    label_type = case.get("retrieval_label_type", "single_source")
    golden_files = _ordered_unique(case.get("golden_source_files", []))
    cited_files = _ordered_unique([item.get("source_file", "") for item in citations])
    retrieved_files = _ordered_unique([item.get("source_file", "") for item in contexts])
    rejected = confidence == 0.0 or not citations

    if expect_rejection:
        return {
            "overall_hit": rejected,
            "retrieval_hit": rejected,
            "citation_hit": rejected,
            "rejected": rejected,
            "golden_files": golden_files,
            "cited_files": cited_files,
            "retrieved_files": retrieved_files,
        }

    if label_type == "multi_source_all_required":
        retrieval_hit = all(golden in retrieved_files for golden in golden_files)
        citation_hit = all(golden in cited_files for golden in golden_files)
    else:
        first_golden = golden_files[0] if golden_files else ""
        retrieval_hit = first_golden in retrieved_files if first_golden else False
        citation_hit = first_golden in cited_files if first_golden else False

    return {
        "overall_hit": retrieval_hit,
        "retrieval_hit": retrieval_hit,
        "citation_hit": citation_hit,
        "rejected": rejected,
        "golden_files": golden_files,
        "cited_files": cited_files,
        "retrieved_files": retrieved_files,
    }


def run(base_url: str) -> dict:
    cases = _load_eval_set()
    details = []
    overall_hits = 0
    retrieval_hits = 0
    citation_hits = 0
    rejections = 0
    latencies = []

    for case in cases:
        payload = {"question": case["question"]}
        t0 = time.time()
        resp = requests.post(f"{base_url.rstrip('/')}/chat", json=payload, timeout=120)
        latency_ms = round((time.time() - t0) * 1000, 2)
        data = resp.json()
        eval_result = _evaluate_case(case, data)

        overall_hits += 1 if eval_result["overall_hit"] else 0
        retrieval_hits += 1 if eval_result["retrieval_hit"] else 0
        citation_hits += 1 if eval_result["citation_hit"] else 0
        rejections += 1 if eval_result["rejected"] else 0
        latencies.append(latency_ms)

        details.append(
            {
                "id": case["id"],
                "question": case["question"],
                "category": case.get("category"),
                "evaluation_group": case.get("evaluation_group"),
                "retrieval_label_type": case.get("retrieval_label_type"),
                "expect_rejection": case.get("expect_rejection", False),
                "golden_source_files": eval_result["golden_files"],
                "retrieved_source_files": eval_result["retrieved_files"],
                "cited_source_files": eval_result["cited_files"],
                "answer": data.get("answer", ""),
                "confidence": data.get("confidence"),
                "latency_ms": latency_ms,
                "retrieval_hit": eval_result["retrieval_hit"],
                "citation_hit": eval_result["citation_hit"],
                "overall_hit": eval_result["overall_hit"],
            }
        )

    total = max(len(cases), 1)
    return {
        "total_cases": len(cases),
        "overall_accuracy": round(overall_hits / total, 3),
        "retrieval_accuracy": round(retrieval_hits / total, 3),
        "citation_accuracy": round(citation_hits / total, 3),
        "rejection_rate": round(rejections / total, 3),
        "p50_latency_ms": _latency_percentile(latencies, 0.5),
        "p90_latency_ms": _latency_percentile(latencies, 0.9),
        "details": details,
    }


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    print(json.dumps(run(base_url), ensure_ascii=False, indent=2))
