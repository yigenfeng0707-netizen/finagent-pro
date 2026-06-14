"""WebSocketManager 单元测试 — 连接管理、广播、心跳、连接数限制"""

import asyncio
from unittest.mock import AsyncMock

import pytest
from websocket_manager import MAX_CONNECTIONS_PER_SESSION, WebSocketManager


@pytest.fixture
def ws_manager():
    return WebSocketManager()


def _make_mock_ws():
    """创建一个模拟 WebSocket 对象"""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


class TestWebSocketConnect:
    """WebSocket 连接管理"""

    @pytest.mark.asyncio
    async def test_connect_accepts_and_registers(self, ws_manager):
        ws = _make_mock_ws()
        await ws_manager.connect("sess1", ws)
        ws.accept.assert_awaited_once()
        assert ws in ws_manager.active_connections["sess1"]

    @pytest.mark.asyncio
    async def test_connect_multiple_sessions(self, ws_manager):
        ws1 = _make_mock_ws()
        ws2 = _make_mock_ws()
        await ws_manager.connect("sess1", ws1)
        await ws_manager.connect("sess2", ws2)
        assert len(ws_manager.active_connections) == 2

    @pytest.mark.asyncio
    async def test_connect_multiple_in_same_session(self, ws_manager):
        ws1 = _make_mock_ws()
        ws2 = _make_mock_ws()
        await ws_manager.connect("sess1", ws1)
        await ws_manager.connect("sess1", ws2)
        assert len(ws_manager.active_connections["sess1"]) == 2

    @pytest.mark.asyncio
    async def test_connect_rejects_when_limit_reached(self, ws_manager):
        """连接数超过上限时，应关闭并拒绝新连接"""
        connections = [_make_mock_ws() for _ in range(MAX_CONNECTIONS_PER_SESSION)]
        for ws in connections:
            await ws_manager.connect("sess1", ws)

        # 已满，再连一个
        extra_ws = _make_mock_ws()
        await ws_manager.connect("sess1", extra_ws)

        # 额外连接应被关闭 (code=1013)
        extra_ws.close.assert_awaited_once()
        close_call = extra_ws.close.call_args
        assert close_call.kwargs.get("code") == 1013 or close_call[1].get("code") == 1013


class TestWebSocketDisconnect:
    """WebSocket 断开连接"""

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, ws_manager):
        ws = _make_mock_ws()
        await ws_manager.connect("sess1", ws)
        ws_manager.disconnect("sess1", ws)
        assert "sess1" not in ws_manager.active_connections

    @pytest.mark.asyncio
    async def test_disconnect_keeps_other_connections(self, ws_manager):
        ws1 = _make_mock_ws()
        ws2 = _make_mock_ws()
        await ws_manager.connect("sess1", ws1)
        await ws_manager.connect("sess1", ws2)
        ws_manager.disconnect("sess1", ws1)
        assert ws2 in ws_manager.active_connections["sess1"]

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_session(self, ws_manager):
        """断开不存在的会话不应抛错"""
        ws = _make_mock_ws()
        ws_manager.disconnect("nonexistent", ws)  # Should not raise


class TestWebSocketBroadcast:
    """WebSocket 消息广播"""

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self, ws_manager):
        from models.schemas import AgentMessage, AgentRole, AgentStatus

        ws1 = _make_mock_ws()
        ws2 = _make_mock_ws()
        await ws_manager.connect("sess1", ws1)
        await ws_manager.connect("sess1", ws2)

        msg = AgentMessage(
            agent="test",
            role=AgentRole.MARKET_ANALYST,
            content="hello",
            status=AgentStatus.COMPLETED,
        )
        await ws_manager.broadcast("sess1", msg)

        ws1.send_json.assert_awaited_once()
        ws2.send_json.assert_awaited_once()
        payload = ws1.send_json.call_args[0][0]
        assert payload["type"] == "agent_progress"

    @pytest.mark.asyncio
    async def test_broadcast_nonexistent_session(self, ws_manager):
        """向不存在的会话广播不应抛错"""
        from models.schemas import AgentMessage, AgentRole, AgentStatus

        msg = AgentMessage(agent="t", role=AgentRole.MARKET_ANALYST, content="x", status=AgentStatus.COMPLETED)
        await ws_manager.broadcast("no_such_session", msg)  # Should not raise

    @pytest.mark.asyncio
    async def test_broadcast_cleans_dead_connections(self, ws_manager):
        """广播时遇到死连接应自动清理"""
        from models.schemas import AgentMessage, AgentRole, AgentStatus

        ws_alive = _make_mock_ws()
        ws_dead = _make_mock_ws()
        ws_dead.send_json = AsyncMock(side_effect=Exception("connection lost"))

        await ws_manager.connect("sess1", ws_alive)
        await ws_manager.connect("sess1", ws_dead)

        msg = AgentMessage(agent="t", role=AgentRole.MARKET_ANALYST, content="x", status=AgentStatus.COMPLETED)
        await ws_manager.broadcast("sess1", msg)

        # 死连接应被清理，存活连接仍在
        assert ws_alive in ws_manager.active_connections["sess1"]
        assert ws_dead not in ws_manager.active_connections["sess1"]


class TestBroadcastFinal:
    """最终报告广播"""

    @pytest.mark.asyncio
    async def test_broadcast_final_sends_report(self, ws_manager):
        ws = _make_mock_ws()
        await ws_manager.connect("sess1", ws)

        report = {"recommendation": "buy", "confidence": 0.85}
        await ws_manager.broadcast_final("sess1", report)

        ws.send_json.assert_awaited_once()
        payload = ws.send_json.call_args[0][0]
        assert payload["type"] == "final_report"
        assert payload["payload"]["recommendation"] == "buy"


class TestBroadcastStatus:
    """状态广播"""

    @pytest.mark.asyncio
    async def test_broadcast_status(self, ws_manager):
        ws = _make_mock_ws()
        await ws_manager.connect("sess1", ws)
        await ws_manager.broadcast_status("sess1", "processing", "分析中")

        ws.send_json.assert_awaited_once()
        payload = ws.send_json.call_args[0][0]
        assert payload["type"] == "status"
        assert payload["payload"]["status"] == "processing"


class TestHeartbeat:
    """心跳机制"""

    @pytest.mark.asyncio
    async def test_heartbeat_cleans_dead_connections(self, ws_manager):
        """心跳应清理无法发送的连接"""
        ws_alive = _make_mock_ws()
        ws_dead = _make_mock_ws()
        ws_dead.send_json = AsyncMock(side_effect=Exception("dead"))

        await ws_manager.connect("sess1", ws_alive)
        await ws_manager.connect("sess1", ws_dead)

        # 启动心跳并让一个周期完成
        task = asyncio.create_task(ws_manager.start_heartbeat(interval=0))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # 死连接应被清理
        assert ws_dead not in ws_manager.active_connections.get("sess1", set())
