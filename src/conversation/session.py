"""会话管理 - 多轮对话上下文"""
import time
import uuid
from typing import Dict, List, Optional


class SessionManager:
    """内存会话管理，生产环境可替换为 Redis"""

    def __init__(self, max_history: int = 5, ttl_seconds: int = 3600):
        self._sessions: Dict[str, dict] = {}
        self.max_history = max_history
        self.ttl = ttl_seconds

    def create_session(self) -> str:
        sid = str(uuid.uuid4())[:8]
        self._sessions[sid] = {
            "created_at": time.time(),
            "last_active": time.time(),
            "messages": [],
        }
        self._cleanup()
        return sid

    def get_history(self, session_id: str, rounds: Optional[int] = None) -> List[dict]:
        session = self._sessions.get(session_id)
        if not session:
            return []
        messages = session["messages"]
        if rounds:
            messages = messages[-(rounds * 2):]  # 每轮 = user + assistant
        return messages

    def add_turn(self, session_id: str, user_msg: str, assistant_msg: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        session["messages"].append({"role": "user", "content": user_msg})
        session["messages"].append({"role": "assistant", "content": assistant_msg})
        session["last_active"] = time.time()

        # 截断历史
        max_msgs = self.max_history * 2
        if len(session["messages"]) > max_msgs:
            session["messages"] = session["messages"][-max_msgs:]

        return True

    def _cleanup(self):
        """清理过期会话"""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s["last_active"] > self.ttl
        ]
        for sid in expired:
            del self._sessions[sid]
