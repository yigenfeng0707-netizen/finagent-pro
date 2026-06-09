import { useEffect, useRef, useCallback } from 'react';

export interface WSMessage {
  type: 'agent_progress' | 'status' | 'final_report';
  payload: any;
}

export interface WSOptions {
  onMessage: (msg: WSMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (err: Event) => void;
  enabled?: boolean;
}

const WS_BASE = process.env.REACT_APP_WS_URL || `ws://${window.location.hostname}:8000`;

export function useWebSocket(sessionId: string | null, options: WSOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const { onMessage, onConnect, onDisconnect, onError, enabled = true } = options;

  const connect = useCallback(() => {
    if (!sessionId || !enabled) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const url = `${WS_BASE}/ws/${sessionId}`;
    const ws = new WebSocket(url);

    ws.onopen = () => {
      wsRef.current = ws;
      onConnect?.();
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        onMessage(msg);
      } catch { /* ignore parse errors */ }
    };

    ws.onclose = () => {
      wsRef.current = null;
      onDisconnect?.();
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = (err) => {
      onError?.(err);
    };
  }, [sessionId, enabled, onMessage, onConnect, onDisconnect, onError]);

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimer.current);
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { disconnect, reconnect: connect };
}
