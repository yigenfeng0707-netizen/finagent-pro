import asyncio
import json
from typing import Any, Dict, Set

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger
from models.schemas import AgentMessage

MAX_CONNECTIONS_PER_SESSION = 5


class WebSocketManager:
    """WebSocket管理器 - 流式推送Agent思考过程，含心跳和连接数限制"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._heartbeat_task: asyncio.Task | None = None

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        if len(self.active_connections[session_id]) >= MAX_CONNECTIONS_PER_SESSION:
            await websocket.close(code=1013, reason="连接数已达上限")
            logger.warning(f"WS连接拒绝: session {session_id} 已达 {MAX_CONNECTIONS_PER_SESSION} 上限")
            return
        self.active_connections[session_id].add(websocket)
        logger.debug(f"WS连接建立: session={session_id}, 当前{len(self.active_connections[session_id])}个")

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, session_id: str, message: AgentMessage):
        if session_id not in self.active_connections:
            return
        payload = {"type": "agent_progress", "payload": message.model_dump()}
        dead_connections = set()
        for ws in self.active_connections[session_id]:
            try:
                await ws.send_json(payload)
            except Exception:
                dead_connections.add(ws)
        for ws in dead_connections:
            self.active_connections[session_id].discard(ws)
        if not self.active_connections.get(session_id):
            self.active_connections.pop(session_id, None)

    async def broadcast_status(self, session_id: str, status: str, message: str = ""):
        if session_id not in self.active_connections:
            return
        payload = {"type": "status", "payload": {"status": status, "message": message}}
        dead = set()
        for ws in self.active_connections[session_id]:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active_connections[session_id].discard(ws)

    async def broadcast_final(self, session_id: str, report: Dict[str, Any]):
        if session_id not in self.active_connections:
            return
        payload = {"type": "final_report", "payload": report}
        dead = set()
        for ws in self.active_connections[session_id]:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active_connections[session_id].discard(ws)

    async def start_heartbeat(self, interval: int = 30):
        """后台心跳任务: 定期ping清理死连接"""
        while True:
            await asyncio.sleep(interval)
            dead_sessions = []
            for session_id, connections in self.active_connections.items():
                dead = set()
                for ws in connections:
                    try:
                        await ws.send_json({"type": "heartbeat", "payload": {"ts": asyncio.get_event_loop().time()}})
                    except Exception:
                        dead.add(ws)
                for ws in dead:
                    connections.discard(ws)
                if not connections:
                    dead_sessions.append(session_id)
            for sid in dead_sessions:
                self.active_connections.pop(sid, None)
            if dead_sessions:
                logger.debug(f"心跳清理: 移除 {len(dead_sessions)} 个空会话")
