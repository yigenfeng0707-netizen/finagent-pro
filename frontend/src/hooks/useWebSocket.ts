import { useEffect, useRef, useCallback } from 'react';

export interface WSMessage {
  type: 'agent_progress' | 'status' | 'final_report';
  payload: Record<string, unknown>;
}

export interface WSOptions {
  onMessage: (msg: WSMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (err: Event) => void;
  enabled?: boolean;
}

const WS_BASE = process.env.REACT_APP_WS_URL || `ws://${window.location.hostname}:8000`;
const MAX_RETRIES = 5;
const BASE_DELAY = 1000;

export function useWebSocket(sessionId: string | null, options: WSOptions & { token?: string }) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const retryCount = useRef(0);

  // Store latest callbacks in refs to prevent re-renders
  const callbacksRef = useRef(options);
  callbacksRef.current = options;

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimer.current);
    if (wsRef.current) {
      wsRef.current.onclose = null; // Prevent reconnect on intentional close
      wsRef.current.close();
      wsRef.current = null;
    }
    retryCount.current = 0;
  }, []);

  const connect = useCallback(() => {
    if (!sessionId || !callbacksRef.current.enabled) return;
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) return;

    let url = `${WS_BASE}/ws/${sessionId}`;
    const token = callbacksRef.current.token;
    if (token) {
      url += `?token=${encodeURIComponent(token)}`;
    }
    const ws = new WebSocket(url);

    ws.onopen = () => {
      wsRef.current = ws;
      retryCount.current = 0;
      callbacksRef.current.onConnect?.();
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        callbacksRef.current.onMessage(msg);
      } catch { /* ignore parse errors */ }
    };

    ws.onclose = () => {
      wsRef.current = null;
      callbacksRef.current.onDisconnect?.();
      // Exponential backoff with jitter, max retries
      if (retryCount.current < MAX_RETRIES) {
        const delay = Math.min(BASE_DELAY * Math.pow(2, retryCount.current), 30000);
        const jitter = delay * 0.2 * Math.random();
        retryCount.current += 1;
        reconnectTimer.current = setTimeout(connect, delay + jitter);
      }
    };

    ws.onerror = (err) => {
      callbacksRef.current.onError?.(err);
    };
  }, [sessionId]);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { disconnect, reconnect: connect };
}
