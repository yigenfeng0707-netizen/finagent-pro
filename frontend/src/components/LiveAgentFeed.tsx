import React, { useEffect, useRef } from 'react';
import { List, Tag, Typography } from 'antd';
import { RobotOutlined } from '@ant-design/icons';

const { Text } = Typography;

export interface AgentFeedMessage {
  agent: string;
  role: string;
  content: string;
  status: string;
  timestamp: string;
  confidence?: number;
  thinking?: string;
}

interface LiveAgentFeedProps {
  messages: AgentFeedMessage[];
  height?: number;
}

const AGENT_COLORS: Record<string, { bg: string; border: string }> = {
  market_analyst: { bg: '#e6f7ff', border: '#91d5ff' },
  sentiment_scanner: { bg: '#fffbe6', border: '#ffe58f' },
  risk_manager: { bg: '#fff1f0', border: '#ffa39e' },
  portfolio_advisor: { bg: '#f6ffed', border: '#b7eb8f' },
  orchestrator: { bg: '#f0f5ff', border: '#adc6ff' },
};

const AGENT_ICONS: Record<string, string> = {
  market_analyst: '市场',
  sentiment_scanner: '情绪',
  risk_manager: '风险',
  portfolio_advisor: '组合',
  orchestrator: '编排',
};

const STATUS_TAG: Record<string, { color: string; text: string }> = {
  completed: { color: 'success', text: '完成' },
  running: { color: 'processing', text: '进行中' },
  pending: { color: 'default', text: '等待' },
  failed: { color: 'error', text: '失败' },
};

const LiveAgentFeed: React.FC<LiveAgentFeedProps> = ({ messages, height = 400 }) => {
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages.length]);

  return (
    <div
      ref={listRef}
      style={{
        height,
        overflowY: 'auto',
        background: '#fafafa',
        borderRadius: 8,
        padding: '8px 0',
      }}
    >
      {messages.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 0', color: '#bbb' }}>
          <RobotOutlined style={{ fontSize: 40, marginBottom: 12, opacity: 0.4 }} />
          <div style={{ fontSize: 14 }}>等待Agent执行...</div>
        </div>
      ) : (
        <List
          dataSource={messages}
          renderItem={(msg: AgentFeedMessage, idx: number) => {
            const colors = AGENT_COLORS[msg.role] || { bg: '#fafafa', border: '#d9d9d9' };
            const st = STATUS_TAG[msg.status] || { color: 'default', text: msg.status };
            return (
              <div
                style={{
                  margin: '6px 12px',
                  padding: '10px 14px',
                  borderRadius: 8,
                  background: colors.bg,
                  border: `1px solid ${colors.border}`,
                  animation: idx === messages.length - 1 ? 'fadeIn 0.3s ease' : undefined,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{
                      width: 28, height: 28, borderRadius: '50%',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      background: colors.border, color: '#fff', fontSize: 12, fontWeight: 'bold',
                    }}>
                      {AGENT_ICONS[msg.role] || '?'}
                    </div>
                    <Text strong style={{ fontSize: 13 }}>{msg.agent}</Text>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {msg.confidence !== undefined && msg.confidence > 0 && (
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        置信度: {(msg.confidence * 100).toFixed(0)}%
                      </Text>
                    )}
                    <Tag color={st.color} style={{ margin: 0, fontSize: 11 }}>{st.text}</Tag>
                    <Text type="secondary" style={{ fontSize: 11 }}>{msg.timestamp}</Text>
                  </div>
                </div>
                <Text style={{ fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                  {msg.content}
                </Text>
              </div>
            );
          }}
        />
      )}
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};

export default LiveAgentFeed;
