"""Small end-to-end latency probe for /chat."""
import argparse
import json
import statistics
import time

import requests


QUESTIONS = [
    "What is the annual leave entitlement for junior employees?",
    "How many days of unused annual leave can be carried over, and by when must it be used?",
    "What is the sick leave entitlement, what evidence is required, and which system records the request?",
    "What is the DBRT notification deadline after breach detection?",
    "What are the main responsibilities of the search service?",
]


def percentile(values, p):
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(len(ordered) * p))
    return ordered[idx]


def main():
    parser = argparse.ArgumentParser(description="Probe /chat latency with fixed questions.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--reuse-session", action="store_true", help="Reuse one session across all questions.")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    session_id = None
    details = []

    for idx, question in enumerate(QUESTIONS, start=1):
        payload = {"question": question}
        if args.reuse_session and session_id:
            payload["session_id"] = session_id

        t0 = time.time()
        resp = requests.post(f"{base}/chat", json=payload, timeout=180)
        elapsed_ms = round((time.time() - t0) * 1000, 2)
        data = resp.json()
        session_id = data.get("session_id", session_id)

        details.append(
            {
                "index": idx,
                "question": question,
                "status_code": resp.status_code,
                "elapsed_ms_client": elapsed_ms,
                "latency_ms_server": data.get("latency_ms"),
                "confidence": data.get("confidence"),
                "session_id": data.get("session_id"),
                "answer_preview": (data.get("answer", "") or "")[:200],
            }
        )

    client_latencies = [item["elapsed_ms_client"] for item in details]
    server_latencies = [item["latency_ms_server"] for item in details if item["latency_ms_server"] is not None]

    result = {
        "reuse_session": args.reuse_session,
        "count": len(details),
        "client_p50_ms": round(statistics.median(client_latencies), 2) if client_latencies else 0.0,
        "client_p90_ms": round(percentile(client_latencies, 0.9), 2),
        "server_p50_ms": round(statistics.median(server_latencies), 2) if server_latencies else 0.0,
        "server_p90_ms": round(percentile(server_latencies, 0.9), 2),
        "details": details,
    }

    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)


if __name__ == "__main__":
    main()
