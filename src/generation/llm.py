"""LLM 调用封装"""
import logging
from typing import List, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


def get_llm_client(
    api_key: str,
    base_url: Optional[str] = None,
) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url or "https://api.deepseek.com/v1")


def generate_answer(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_query: str,
    contexts: List[dict],
    temperature: float = 0.1,
    max_tokens: int = 1024,
) -> dict:
    """
    调用 LLM 生成答案
    Returns: {"answer": str, "input_tokens": int, "output_tokens": int}
    """
    # 构建带编号的上下文
    context_text = _format_contexts(contexts)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {user_query}"},
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    answer = response.choices[0].message.content
    usage = response.usage

    return {
        "answer": answer,
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.completion_tokens,
    }


def rewrite_query(
    client: OpenAI,
    model: str,
    history: List[dict],
    current_query: str,
) -> str:
    """结合历史改写为独立可检索查询"""
    history_text = ""
    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"

    prompt = f"""Based on the conversation history, rewrite the current question into a standalone, self-contained query that can be used for document retrieval. Resolve any pronouns and fill in missing context.

Conversation:
{history_text}
Current question: {current_query}

Rewritten query:"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=200,
    )
    return response.choices[0].message.content.strip()


def _format_contexts(contexts: List[dict]) -> str:
    """格式化检索上下文为带编号的引用格式"""
    parts = []
    for i, ctx in enumerate(contexts, start=1):
        source = ctx.get("source_file", "unknown")
        page = ctx.get("page_number", 1)
        text = ctx.get("text", "")
        parts.append(f"[{i}] {source} §{page}:\n{text}")
    return "\n\n".join(parts)
