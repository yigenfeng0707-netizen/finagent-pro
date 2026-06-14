"""SessionMemory 单元测试 — 会话持久化、历史、偏好、路径穿越防护"""

import json
import os
import tempfile

import pytest
from memory.session_memory import SessionMemory


@pytest.fixture
def memory_store(tmp_path):
    """使用临时目录避免测试污染"""
    return SessionMemory(persist_dir=str(tmp_path))


class TestSessionSaveLoad:
    """会话保存和加载"""

    def test_save_and_load_session(self, memory_store):
        data = {"query": "分析腾讯", "result": "买入"}
        memory_store.save_session("sess001", data)
        loaded = memory_store.load_session("sess001")
        assert loaded is not None
        assert loaded["query"] == "分析腾讯"
        assert loaded["result"] == "买入"
        assert "_updated_at" in loaded  # 自动添加时间戳

    def test_load_nonexistent_returns_none(self, memory_store):
        assert memory_store.load_session("nonexistent") is None

    def test_save_overwrites_previous(self, memory_store):
        memory_store.save_session("sess001", {"v": 1})
        memory_store.save_session("sess001", {"v": 2})
        loaded = memory_store.load_session("sess001")
        assert loaded["v"] == 2


class TestSessionHistory:
    """对话历史管理"""

    def test_append_and_get_history(self, memory_store):
        memory_store.append_history("sess001", "user", "分析腾讯")
        memory_store.append_history("sess001", "assistant", "腾讯走势分析...")
        history = memory_store.get_history("sess001")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_get_history_empty_session(self, memory_store):
        assert memory_store.get_history("no_such_sess") == []

    def test_get_history_limit(self, memory_store):
        for i in range(20):
            memory_store.append_history("sess001", "user", f"msg_{i}")
        history = memory_store.get_history("sess001", limit=5)
        assert len(history) == 5
        # 应返回最近5条 (msg_15 ~ msg_19)
        assert history[-1]["content"] == "msg_19"

    def test_append_history_preserves_data(self, memory_store):
        """追加历史不应覆盖已有偏好"""
        memory_store.save_preference("sess001", "risk", "moderate")
        memory_store.append_history("sess001", "user", "hello")
        loaded = memory_store.load_session("sess001")
        assert loaded["preferences"]["risk"] == "moderate"
        assert len(loaded["history"]) == 1


class TestSessionPreferences:
    """偏好管理"""

    def test_save_and_get_preference(self, memory_store):
        memory_store.save_preference("sess001", "risk_profile", "aggressive")
        assert memory_store.get_preference("sess001", "risk_profile") == "aggressive"

    def test_get_preference_default(self, memory_store):
        assert memory_store.get_preference("sess001", "missing_key", "default_val") == "default_val"

    def test_get_preference_nonexistent_session(self, memory_store):
        assert memory_store.get_preference("no_sess", "key", 42) == 42

    def test_save_multiple_preferences(self, memory_store):
        memory_store.save_preference("sess001", "risk", "low")
        memory_store.save_preference("sess001", "market", "hk")
        loaded = memory_store.load_session("sess001")
        assert loaded["preferences"]["risk"] == "low"
        assert loaded["preferences"]["market"] == "hk"


class TestPathTraversalProtection:
    """路径穿越防护 — session_id 只允许 [a-zA-Z0-9_-]"""

    def test_rejects_dot_dot_slash(self, memory_store):
        with pytest.raises(ValueError, match="非法session_id"):
            memory_store.load_session("../../etc/passwd")

    def test_rejects_path_separator(self, memory_store):
        with pytest.raises(ValueError, match="非法session_id"):
            memory_store.load_session("sess/sub")

    def test_rejects_special_chars(self, memory_store):
        with pytest.raises(ValueError, match="非法session_id"):
            memory_store.save_session("sess@!#$", {})

    def test_rejects_empty_id(self, memory_store):
        with pytest.raises(ValueError, match="非法session_id"):
            memory_store.load_session("")

    def test_accepts_valid_ids(self, memory_store):
        valid_ids = ["sess-001", "ABC_123", "a" * 128, "simple"]
        for sid in valid_ids:
            memory_store.save_session(sid, {"ok": True})
            assert memory_store.load_session(sid)["ok"] is True

    def test_rejects_too_long_id(self, memory_store):
        with pytest.raises(ValueError, match="非法session_id"):
            memory_store.load_session("a" * 129)
