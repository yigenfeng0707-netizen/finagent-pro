import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

# 仅允许字母、数字、下划线和短横线，防止路径穿越
_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")


class SessionMemory:
    """基于文件的会话记忆系统"""

    def __init__(self, persist_dir: str = "./memory_store"):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)

    def _session_path(self, session_id: str) -> str:
        if not _SESSION_ID_RE.match(session_id):
            raise ValueError("非法session_id: 仅允许字母、数字、下划线和短横线")
        return os.path.join(self.persist_dir, f"{session_id}.json")

    def save_session(self, session_id: str, data: Dict[str, Any]):
        path = self._session_path(session_id)
        data["_updated_at"] = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        path = self._session_path(session_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def append_history(self, session_id: str, role: str, content: str):
        data = self.load_session(session_id) or {"history": [], "preferences": {}}
        data.setdefault("history", []).append(
            {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        )
        self.save_session(session_id, data)

    def get_history(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        data = self.load_session(session_id)
        if not data:
            return []
        return data.get("history", [])[-limit:]

    def save_preference(self, session_id: str, key: str, value: Any):
        data = self.load_session(session_id) or {"history": [], "preferences": {}}
        data.setdefault("preferences", {})[key] = value
        self.save_session(session_id, data)

    def get_preference(self, session_id: str, key: str, default: Any = None) -> Any:
        data = self.load_session(session_id)
        if not data:
            return default
        return data.get("preferences", {}).get(key, default)
