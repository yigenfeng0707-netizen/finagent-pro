import React from 'react';
import { Row, Col, Card, Input, Button, message } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import LiveAgentFeed from './LiveAgentFeed';
import AgentThinkingPanel from './AgentThinkingPanel';
import { useAppStore } from '../stores/appStore';
import { API_BASE } from '../constants';
import { useState } from 'react';

const AgentChatPage: React.FC = () => {
  const feedMessages = useAppStore(s => s.feedMessages);
  const thinkingSteps = useAppStore(s => s.thinkingSteps);
  const sessionId = useAppStore(s => s.sessionId);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState<Array<{role: string; content: string}>>([]);

  const handleSendChat = async () => {
    if (!chatInput.trim()) return;
    const userMsg = chatInput.trim();
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setChatLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, session_id: sessionId || undefined }),
      });
      const data = await response.json();
      if (data.type === 'analysis_complete' && data.data) {
        setChatMessages(prev => [...prev, { role: 'assistant', content: '分析已完成，请查看投资仪表盘查看详细结果。' }]);
        useAppStore.getState().setAnalysisResult(data.data);
      } else if (data.message) {
        setChatMessages(prev => [...prev, { role: 'assistant', content: data.message }]);
      }
    } catch {
      message.error('对话请求失败');
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <Row gutter={[16, 16]} style={{ height: 'calc(100vh - 200px)' }}>
      <Col span={14}>
        <Card title="Agent实时消息流" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <div style={{ flex: 1, overflow: 'auto', marginBottom: 16 }}>
            {chatMessages.map((msg, i) => (
              <div key={i} style={{
                marginBottom: 8,
                textAlign: msg.role === 'user' ? 'right' : 'left',
              }}>
                <span style={{
                  display: 'inline-block',
                  padding: '8px 12px',
                  borderRadius: 8,
                  background: msg.role === 'user' ? '#1890ff' : '#f0f0f0',
                  color: msg.role === 'user' ? '#fff' : '#333',
                  maxWidth: '80%',
                }}>
                  {msg.content}
                </span>
              </div>
            ))}
            {feedMessages.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <LiveAgentFeed messages={feedMessages} height={300} />
              </div>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <Input
              placeholder="输入消息，如：分析腾讯、帮我看看美团..."
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              onPressEnter={handleSendChat}
              disabled={chatLoading}
            />
            <Button type="primary" icon={<SendOutlined />} onClick={handleSendChat} loading={chatLoading} />
          </div>
        </Card>
      </Col>
      <Col span={10}>
        <AgentThinkingPanel steps={thinkingSteps} />
      </Col>
    </Row>
  );
};

export default AgentChatPage;
