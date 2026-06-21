"""OpenAI-compatible LLM helpers."""
import json
import logging
import time
from typing import List, Optional

from openai import OpenAI

logger = logging.getLogger("rag-qa.llm")


def _log_llm_call(call_type: str, model: str, started_at: float, usage=None, **extra):
    entry = {
        "event": "llm.call",
        "call_type": call_type,
        "model": model,
        "latency_ms": round((time.time() - started_at) * 1000, 2),
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
        **extra,
    }
    logger.info(json.dumps(entry, ensure_ascii=False))


def get_llm_client(api_key: str, base_url: Optional[str] = None) -> OpenAI:
    return OpenAI(
        api_key=api_key,
        base_url=base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )


def _format_contexts(contexts: List[dict]) -> str:
    parts = []
    for i, ctx in enumerate(contexts, start=1):
        title = ctx.get("doc_title", "")
        section_path = ctx.get("section_path", "")
        department = ctx.get("department", "General")
        source = ctx.get("source_file", "unknown")
        page = ctx.get("page_number", 1)
        text = ctx.get("text", "")
        header_lines = [f"Document: {title or source}"]
        if section_path:
            header_lines.append(f"Section Path: {section_path}")
        header_lines.append(f"Department: {department}")
        header_lines.append("")
        header_lines.append("Content:")
        header_lines.append(text)
        parts.append(f"[{i}] {source} p.{page}\n" + "\n".join(header_lines))
    return "\n\n".join(parts)


def generate_answer(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_query: str,
    contexts: List[dict],
    temperature: float = 0.1,
    max_tokens: int = 1024,
) -> dict:
    context_text = _format_contexts(contexts)
    started_at = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Retrieved context:\n{context_text}\n\nQuestion: {user_query}",
            },
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    answer = response.choices[0].message.content or ""
    usage = response.usage
    _log_llm_call(
        "generate_answer",
        model,
        started_at,
        usage=usage,
        context_count=len(contexts),
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return {
        "answer": answer.strip(),
        "input_tokens": getattr(usage, "prompt_tokens", 0),
        "output_tokens": getattr(usage, "completion_tokens", 0),
    }


def rewrite_query(client: OpenAI, model: str, history: List[dict], current_query: str) -> str:
    history_text = []
    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_text.append(f"{role}: {msg['content']}")

    prompt = (
        "Rewrite the user's latest question into a standalone retrieval query. "
        "Resolve pronouns and missing references using the chat history. "
        "Keep the rewritten query concise and factual.\n\n"
        f"Conversation:\n{chr(10).join(history_text)}\n\n"
        f"Current question: {current_query}\n\n"
        "Rewritten query:"
    )
    started_at = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=200,
    )
    rewritten = response.choices[0].message.content or ""
    _log_llm_call(
        "rewrite_query",
        model,
        started_at,
        usage=response.usage,
        history_messages=len(history),
        max_tokens=200,
    )
    return rewritten.strip() or current_query
