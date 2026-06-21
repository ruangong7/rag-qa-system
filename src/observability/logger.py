"""Structured JSON logging for RAG requests."""
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional


class RAGLogger:
    def __init__(self, name: str = "rag-qa"):
        self.logger = logging.getLogger(name)
        if self.logger.handlers:
            return

        self.logger.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))
        self.logger.propagate = False

        formatter = logging.Formatter("%(message)s")
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)

        if os.getenv("LOG_TO_FILE", "true").lower() in {"1", "true", "yes", "on"}:
            log_dir = Path(os.getenv("LOG_DIR", "logs"))
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_dir / os.getenv("LOG_FILE", "rag.jsonl"), encoding="utf-8")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _ts(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

    def log_request(
        self,
        request_id: str,
        session_id: str,
        query: str,
        stages: Dict[str, Any],
        answer: str = "",
        total_latency_ms: float = 0,
        tokens: Optional[dict] = None,
        rejection: bool = False,
        rejection_reason: str = "",
        status: str = "ok",
        trace_id: str = "",
        span_id: str = "",
        traceparent: str = "",
    ):
        entry = {
            "timestamp": self._ts(),
            "level": "INFO",
            "event": "rag.request",
            "request_id": request_id,
            "session_id": session_id,
            "status": status,
            "trace_id": trace_id,
            "span_id": span_id,
            "traceparent": traceparent,
            "query": query,
            "answer_preview": answer[:300],
            "total_latency_ms": round(total_latency_ms, 2),
            "tokens": tokens or {},
            "rejection": rejection,
            "rejection_reason": rejection_reason,
            "stages": stages,
        }
        self.logger.info(json.dumps(entry, ensure_ascii=False))

    def log_alert(self, request_id: str, message: str, **kwargs):
        entry = {
            "timestamp": self._ts(),
            "level": "WARNING",
            "event": "rag.alert",
            "request_id": request_id,
            "message": message,
            **kwargs,
        }
        self.logger.warning(json.dumps(entry, ensure_ascii=False))

    def log_error(self, request_id: str, message: str, exc: Exception, **kwargs):
        entry = {
            "timestamp": self._ts(),
            "level": "ERROR",
            "event": "rag.error",
            "request_id": request_id,
            "message": message,
            "error": str(exc),
            **kwargs,
        }
        self.logger.error(json.dumps(entry, ensure_ascii=False))
