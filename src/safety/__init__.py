"""Minimal prompt-injection checks and PII input masking."""
import re


INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous",
    r"ignore\s+(all\s+)?above",
    r"system\s*:",
    r"override\s+(system\s+)?prompt",
    r"forget\s+(all|everything)",
    r"disregard\s+(all|previous)",
    r"new\s+instructions?\s*:",
    r"pretend\s+(you\s+are|to\s+be)",
    r"jailbreak",
    r"dan\s+mode",
    r"你现在是",
    r"你是一个",
    r"角色扮演",
    r"扮演",
]
INJECTION_REGEX = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

PII_PATTERNS = {
    "cn_id_card": re.compile(r"[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]"),
    "cn_phone": re.compile(r"1[3-9]\d{9}"),
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "bank_card": re.compile(r"\b\d{16,19}\b"),
}

REJECTION_TEMPLATES = {
    "no_results": "抱歉，当前知识库中没有找到与您问题相关的信息。请尝试换一种方式提问，或联系管理员补充相关资料。",
    "low_confidence": "当前知识库未能提供足够的相关信息来准确回答您的问题。建议您核实其他来源或咨询相关部门。",
    "injection": "您的输入包含不被允许的内容，请重新提问。",
    "unsupported_answer": "当前检索到的上下文不足以支持一个可验证的答案，因此我不能基于现有资料作答。",
}


def check_injection(query: str) -> tuple[bool, str]:
    if len(query) > 2000:
        return False, "query_too_long"
    match = INJECTION_REGEX.search(query)
    if match:
        return False, f"injection:{match.group()}"
    return True, "ok"


def mask_pii(text: str) -> tuple[str, int]:
    masked = text
    count = 0
    for name, pattern in PII_PATTERNS.items():
        masked, n = pattern.subn(f"<{name.upper()}_MASKED>", masked)
        count += n
    return masked, count
