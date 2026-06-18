"""Post-processing - 引用校验 + PII 脱敏"""
import re
import logging

logger = logging.getLogger(__name__)


def validate_citations(answer: str, num_contexts: int) -> dict:
    """
    校验答案中的引用格式 [N]
    Returns: {"valid": bool, "citations_found": int, "citations_expected": int}
    """
    pattern = r"\[(\d+)\]"
    found = set(int(m) for m in re.findall(pattern, answer))
    valid_citations = [n for n in found if 1 <= n <= num_contexts]
    invalid_citations = [n for n in found if n < 1 or n > num_contexts]

    return {
        "valid": len(invalid_citations) == 0 and len(valid_citations) > 0,
        "citations_found": len(valid_citations),
        "citations_invalid": invalid_citations,
        "citations_total": num_contexts,
    }


def check_answer_faithfulness(answer: str, contexts: list) -> float:
    """
    快速忠实度检查：答案长度 / 上下文总长度 比率
    比率过高 → 可能包含幻觉（因为答案超出了检索内容的覆盖范围）
    """
    context_text = " ".join(c.get("text", "") for c in contexts)
    if not context_text:
        return 0.0

    ratio = len(answer) / len(context_text)
    return min(ratio, 1.0)


# PII patterns
PII_PATTERNS = {
    "cn_id_card": re.compile(r"[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]"),
    "cn_phone": re.compile(r"1[3-9]\d{9}"),
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "bank_card": re.compile(r"\d{16,19}"),
}


def mask_pii(text: str) -> str:
    """PII 脱敏"""
    masked = text
    for name, pattern in PII_PATTERNS.items():
        masked = pattern.sub(f"<{name.upper()}_MASKED>", masked)
    return masked
