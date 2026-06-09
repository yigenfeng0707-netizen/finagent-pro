import asyncio
import json
from typing import Set, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from models.schemas import AgentMessage


class WebSocketManager:
    """WebSocket管理器 - 流式推送Agent思考过程"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, session_id: str, message: AgentMessage):
        if session_id not in self.active_connections:
            return
        payload = {
            "type": "agent_progress",
            "payload": message.model_dump()
        }
        dead_connections = set()
        for ws in self.active_connections[session_id]:
            try:
                await ws.send_json(payload)
            except Exception:
                dead_connections.add(ws)
        for ws in dead_connections:
            self.active_connections[session_id].discard(ws)

    async def broadcast_status(self, session_id: str, status: str, message: str = ""):
        if session_id not in self.active_connections:
            return
        payload = {
            "type": "status",
            "payload": {"status": status, "message": message}
        }
        for ws in self.active_connections[session_id]:
            try:
                await ws.send_json(payload)
            except Exception:
                pass

    async def broadcast_final(self, session_id: str, report: Dict[str, Any]):
        if session_id not in self.active_connections:
            return
        payload = {
            "type": "final_report",
            "payload": report
        }
        for ws in self.active_connections[session_id]:
            try:
                await ws.send_json(payload)
            except Exception:
                pass
