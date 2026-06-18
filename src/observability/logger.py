"""结构化日志 - JSON格式，面向 ELK/Grafana 消费"""
import json
import time
import logging
from typing import Any, Dict, Optional


class RAGLogger:
    """结构化日志记录器"""

    def __init__(self, name: str = "rag-qa"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

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
    ):
        """记录完整请求日志"""
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "level": "INFO",
            "request_id": request_id,
            "session_id": session_id,
            "query": query,
            "answer": answer[:200] + "..." if len(answer) > 200 else answer,
            "total_latency_ms": round(total_latency_ms, 2),
            "tokens": tokens or {},
            "rejection": rejection,
            "rejection_reason": rejection_reason,
            "stages": stages,
        }
        self.logger.info(json.dumps(entry, ensure_ascii=False))

    def log_stage(self, request_id: str, stage: str, **kwargs):
        """记录单个阶段"""
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "level": "DEBUG",
            "request_id": request_id,
            "stage": stage,
            **kwargs,
        }
        self.logger.debug(json.dumps(entry, ensure_ascii=False))

    def log_alert(self, request_id: str, message: str, **kwargs):
        """告警日志"""
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "level": "WARN",
            "request_id": request_id,
            "message": message,
            **kwargs,
        }
        self.logger.warning(json.dumps(entry, ensure_ascii=False))
