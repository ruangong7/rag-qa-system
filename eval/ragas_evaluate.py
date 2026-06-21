"""Run RAGAS faithfulness and context-precision evaluation against /chat."""
import argparse
import asyncio
import json
import math
import os
import sys
import types
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import AsyncOpenAI


def _install_ragas_import_stubs():
    """Patch missing optional langchain_community VertexAI modules for ragas import."""
    try:
        import langchain_community.chat_models.vertexai  # noqa: F401
    except Exception:
        chat_models_mod = sys.modules.get("langchain_community.chat_models")
        if chat_models_mod is None:
            chat_models_mod = types.ModuleType("langchain_community.chat_models")
            sys.modules["langchain_community.chat_models"] = chat_models_mod

        vertexai_mod = types.ModuleType("langchain_community.chat_models.vertexai")

        class ChatVertexAI:  # pragma: no cover - import shim
            pass

        vertexai_mod.ChatVertexAI = ChatVertexAI
        sys.modules["langchain_community.chat_models.vertexai"] = vertexai_mod
        setattr(chat_models_mod, "vertexai", vertexai_mod)

    try:
        import langchain_community.llms as lc_llms

        if not hasattr(lc_llms, "VertexAI"):
            class VertexAI:  # pragma: no cover - import shim
                pass

            lc_llms.VertexAI = VertexAI
    except Exception:
        llms_mod = types.ModuleType("langchain_community.llms")

        class VertexAI:  # pragma: no cover - import shim
            pass

        llms_mod.VertexAI = VertexAI
        sys.modules["langchain_community.llms"] = llms_mod


def _load_ragas_objects():
    _install_ragas_import_stubs()

    from ragas.llms import llm_factory
    from ragas.metrics.collections import ContextPrecisionWithoutReference, Faithfulness

    return (
        llm_factory,
        Faithfulness,
        ContextPrecisionWithoutReference,
    )


def _mean(values):
    numeric = [float(v) for v in values if v is not None and not math.isnan(float(v))]
    return round(sum(numeric) / len(numeric), 3) if numeric else None


def _load_eval_set(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _collect_chat_samples(base_url: str, eval_cases: list[dict], timeout: int):
    samples = []
    sample_meta = []
    errors = []

    for case in eval_cases:
        payload = {"question": case["question"]}
        try:
            resp = requests.post(
                f"{base_url.rstrip('/')}/chat",
                json=payload,
                timeout=timeout,
            )
            data = resp.json()
        except Exception as exc:
            errors.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "error": str(exc),
                }
            )
            continue

        if not resp.ok:
            errors.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "status_code": resp.status_code,
                    "error": data,
                }
            )
            continue

        contexts = [item.get("snippet", "") for item in data.get("retrieved_contexts", []) if item.get("snippet")]
        answer = data.get("answer", "")
        if not answer or not contexts:
            errors.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "error": "missing answer or retrieved contexts",
                    "response": data,
                }
            )
            continue

        samples.append(
            {
                "user_input": case["question"],
                "retrieved_contexts": contexts,
                "response": answer,
            }
        )
        sample_meta.append(
            {
                "id": case["id"],
                "question": case["question"],
                "category": case.get("category"),
                "evaluation_group": case.get("evaluation_group"),
                "language": case.get("language"),
                "api_latency_ms": data.get("latency_ms"),
                "retrieved_context_count": len(contexts),
                "confidence": data.get("confidence"),
                "citations": data.get("citations", []),
                "response": answer,
                "retrieved_contexts": contexts,
            }
        )

    return samples, sample_meta, errors


async def _score_samples(samples, sample_meta, judge_llm, Faithfulness, ContextPrecisionWithoutReference):
    faithfulness_metric = Faithfulness(llm=judge_llm)
    context_precision_metric = ContextPrecisionWithoutReference(llm=judge_llm)

    details = []
    errors = []

    for idx, (sample, meta) in enumerate(zip(samples, sample_meta), start=1):
        try:
            faithfulness_result = await faithfulness_metric.ascore(
                user_input=sample["user_input"],
                response=sample["response"],
                retrieved_contexts=sample["retrieved_contexts"],
            )
            context_precision_result = await context_precision_metric.ascore(
                user_input=sample["user_input"],
                response=sample["response"],
                retrieved_contexts=sample["retrieved_contexts"],
            )
            details.append(
                {
                    **meta,
                    "faithfulness": faithfulness_result.value,
                    "context_precision_without_reference": context_precision_result.value,
                    "index": idx,
                }
            )
        except Exception as exc:
            errors.append(
                {
                    "id": meta["id"],
                    "question": meta["question"],
                    "error": str(exc),
                }
            )

    return details, errors


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run RAGAS faithfulness and context precision on /chat.")
    parser.add_argument("base_url", nargs="?", default="http://127.0.0.1:8000")
    parser.add_argument("--eval-set", default="eval/eval_set.json")
    parser.add_argument("--out", default="docs/ragas_eval.json")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--include-rejections", action="store_true")
    args = parser.parse_args()

    judge_api_key = os.getenv("RAGAS_LLM_API_KEY") or os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    judge_base_url = os.getenv("RAGAS_LLM_BASE_URL") or os.getenv("LLM_BASE_URL")
    judge_model = os.getenv("RAGAS_LLM_MODEL", "gpt-4o-mini")
    judge_temperature = float(os.getenv("RAGAS_LLM_TEMPERATURE", "0.0"))
    judge_max_tokens = int(os.getenv("RAGAS_LLM_MAX_TOKENS", "4096"))

    if not judge_api_key:
        raise RuntimeError("Missing RAGAS_LLM_API_KEY / LLM_API_KEY / DASHSCOPE_API_KEY.")

    print(f"Collecting /chat samples from {args.base_url} ...")
    eval_cases = _load_eval_set(args.eval_set)
    if not args.include_rejections:
        eval_cases = [c for c in eval_cases if not c.get("expect_rejection", False)]
    if args.limit > 0:
        eval_cases = eval_cases[: args.limit]

    samples, sample_meta, errors = _collect_chat_samples(args.base_url, eval_cases, args.timeout)
    if not samples:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")
        raise RuntimeError("No successful /chat samples collected.")

    llm_factory, Faithfulness, ContextPrecisionWithoutReference = _load_ragas_objects()

    judge_client = AsyncOpenAI(api_key=judge_api_key, base_url=judge_base_url)
    judge_llm = llm_factory(
        judge_model,
        client=judge_client,
        temperature=judge_temperature,
        max_tokens=judge_max_tokens,
    )
    print(f"Running Ragas on {len(samples)} samples ...")
    details, metric_errors = asyncio.run(
        _score_samples(
            samples,
            sample_meta,
            judge_llm,
            Faithfulness,
            ContextPrecisionWithoutReference,
        )
    )
    errors.extend(metric_errors)

    faithfulness_scores = [item.get("faithfulness") for item in details]
    context_precision_scores = [item.get("context_precision_without_reference") for item in details]

    output = {
        "evaluation_type": "ragas",
        "evaluated_cases": len(details),
        "requested_cases": len(eval_cases),
        "skipped_cases": len(errors),
        "faithfulness": _mean(faithfulness_scores),
        "context_precision_without_reference": _mean(context_precision_scores),
        "metrics": ["faithfulness", "context_precision_without_reference"],
        "judge_model": judge_model,
        "judge_base_url": judge_base_url,
        "details": details,
        "errors": errors,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Ragas Evaluation Summary")
    print("=" * 60)
    print(f"evaluated_cases: {output['evaluated_cases']}")
    print(f"faithfulness: {output['faithfulness']}")
    print(f"context_precision_without_reference: {output['context_precision_without_reference']}")
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
