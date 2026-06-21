"""Tiny tracing helpers."""
import secrets


def parse_or_create_trace(headers: dict) -> dict:
    traceparent = headers.get("traceparent", "")
    if traceparent:
        parts = traceparent.split("-")
        if len(parts) >= 4:
            return {
                "trace_id": parts[1],
                "span_id": secrets.token_hex(8),
                "parent_span_id": parts[2],
            }
    return {
        "trace_id": secrets.token_hex(16),
        "span_id": secrets.token_hex(8),
        "parent_span_id": "",
    }


def build_traceparent(ctx: dict) -> str:
    return f"00-{ctx['trace_id']}-{ctx['span_id']}-01"
