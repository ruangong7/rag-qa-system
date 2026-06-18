"""安全防护 - Prompt注入检测 + PII脱敏"""
import re
import logging

logger = logging.getLogger(__name__)

# 注入模式列表
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous",
    r"ignore\s+(all\s+)?above",
    r"system\s*:",
    r"你是一个",
    r"你现在是",
    r"pretend\s+(you\s+are|to\s+be)",
    r"forget\s+(all|everything)",
    r"disregard\s+(all|previous)",
    r"new\s+instructions?\s*:",
    r"override\s+(system\s+)?prompt",
    r"扮演",
    r"角色扮演",
    r"jailbreak",
    r"dan\s+mode",
]

INJECTION_REGEX = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

MAX_QUERY_LENGTH = 2000


def check_injection(query: str) -> tuple[bool, str]:
    """
    检测 Prompt 注入
    Returns: (is_safe, reason)
    """
    # 长度检查
    if len(query) > MAX_QUERY_LENGTH:
        return False, f"Query too long ({len(query)} > {MAX_QUERY_LENGTH})"

    # 注入模式匹配
    match = INJECTION_REGEX.search(query)
    if match:
        return False, f"Injection pattern detected: '{match.group()}'"

    return True, "ok"


"""
PII patterns compiled for reuse
"""
PII_PATTERNS = {
    "cn_id_card": re.compile(r"[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]"),
    "cn_phone": re.compile(r"1[3-9]\d{9}"),
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "bank_card": re.compile(r"\d{16,19}"),
}


def mask_pii(text: str) -> tuple[str, int]:
    """PII 脱敏，返回 (脱敏后文本, 脱敏数量)"""
    count = 0
    masked = text
    for name, pattern in PII_PATTERNS.items():
        new_text, n = pattern.subn(f"<{name.upper()}_MASKED>", masked)
        if n > 0:
            count += n
            masked = new_text
    return masked, count


REJECTION_TEMPLATES = {
    "no_results": "抱歉，当前知识库中没有找到与您问题相关的信息。请尝试换一种方式提问，或联系管理员补充相关资料。",
    "low_confidence": "当前知识库未能提供足够的相关信息来准确回答您的问题。建议您核实其他来源或咨询相关部门。",
    "injection": "您的输入包含不被允许的内容，请重新提问。",
}
