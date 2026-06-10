import React from 'react';
import { Row, Col, Card } from 'antd';
import LiveAgentFeed from './LiveAgentFeed';
import AgentThinkingPanel from './AgentThinkingPanel';

export interface AgentChatPageProps {
  feedMessages: any[];
  thinkingSteps: any[];
}

const AgentChatPage: React.FC<AgentChatPageProps> = ({ feedMessages, thinkingSteps }) => (
  <Row gutter={[16, 16]} style={{ height: 'calc(100vh - 200px)' }}>
    <Col span={14}>
      <Card title="Agent实时消息流" style={{ height: '100%' }}>
        <LiveAgentFeed messages={feedMessages} height={window.innerHeight - 320} />
      </Card>
    </Col>
    <Col span={10}>
      <AgentThinkingPanel steps={thinkingSteps} />
    </Col>
  </Row>
);

export default AgentChatPage;
