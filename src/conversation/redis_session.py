"""Redis-backed session manager."""
import json

import redis


class RedisSessionManager:
    def __init__(self, redis_url: str, max_history: int = 5, ttl_seconds: int = 3600):
        self.client = redis.from_url(redis_url, decode_responses=True)
        self.max_history = max_history
        self.ttl_seconds = ttl_seconds

    def ping(self):
        return self.client.ping()

    def _key(self, session_id: str) -> str:
        return f"rag:session:{session_id}"

    def create_session(self) -> str:
        import uuid

        sid = str(uuid.uuid4())[:8]
        self.client.setex(self._key(sid), self.ttl_seconds, json.dumps([]))
        return sid

    def get_history(self, session_id: str, rounds: int | None = None):
        raw = self.client.get(self._key(session_id))
        if not raw:
            return []
        messages = json.loads(raw)
        if rounds:
            messages = messages[-(rounds * 2) :]
        return messages

    def add_turn(self, session_id: str, user_msg: str, assistant_msg: str) -> bool:
        key = self._key(session_id)
        raw = self.client.get(key)
        if raw is None:
            return False
        messages = json.loads(raw)
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": assistant_msg})
        max_msgs = self.max_history * 2
        if len(messages) > max_msgs:
            messages = messages[-max_msgs:]
        self.client.setex(key, self.ttl_seconds, json.dumps(messages, ensure_ascii=False))
        return True
