"""Citation validation and PII masking."""
import re


def validate_citations(answer: str, num_contexts: int) -> dict:
    pattern = r"\[(\d+)\]"
    found = [int(m) for m in re.findall(pattern, answer)]
    valid = [n for n in found if 1 <= n <= num_contexts]
    invalid = [n for n in found if n < 1 or n > num_contexts]
    return {
        "valid": len(valid) > 0 and not invalid,
        "citations_found": len(valid),
        "citations_valid": sorted(set(valid)),
        "citations_invalid": sorted(set(invalid)),
        "citations_total": num_contexts,
    }


PII_PATTERNS = {
    "cn_id_card": re.compile(r"[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]"),
    "cn_phone": re.compile(r"1[3-9]\d{9}"),
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "bank_card": re.compile(r"\b\d{16,19}\b"),
}


def mask_pii(text: str) -> str:
    masked = text
    for name, pattern in PII_PATTERNS.items():
        masked = pattern.sub(f"<{name.upper()}_MASKED>", masked)
    return masked
