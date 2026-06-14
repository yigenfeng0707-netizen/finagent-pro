import React from 'react';
import { Card, Tag, Typography, Steps, Empty } from 'antd';
import {
  LoadingOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined,
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;

export interface ThinkingStep {
  stepId: number;
  agent: string;
  role: string;
  content: string;
  thinking?: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  timestamp: string;
  confidence?: number;
  data?: Record<string, unknown>;
}

interface AgentThinkingPanelProps {
  steps: ThinkingStep[];
}

const ROLE_NAMES: Record<string, string> = {
  market_analyst: '市场分析师',
  sentiment_scanner: '情绪扫描器',
  risk_manager: '风险经理',
  portfolio_advisor: '组合顾问',
  orchestrator: '编排器',
};

const AgentThinkingPanel: React.FC<AgentThinkingPanelProps> = ({ steps }) => {
  const currentIdx = steps.findIndex(s => s.status === 'running');

  return (
    <Card
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>Agent思考过程</span>
          {steps.some(s => s.status === 'running') && (
            <Tag icon={<LoadingOutlined />} color="processing">分析中</Tag>
          )}
        </div>
      }
      style={{ height: '100%' }}
    >
      {steps.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无Agent执行记录"
        />
      ) : (
        <Steps
          direction="vertical"
          size="small"
          current={currentIdx >= 0 ? currentIdx : steps.length}
          items={steps.map((step) => ({
            status:
              step.status === 'completed' ? 'finish' :
              step.status === 'running' ? 'process' :
              step.status === 'failed' ? 'error' : 'wait',
            icon:
              step.status === 'completed' ? <CheckCircleOutlined /> :
              step.status === 'running' ? <LoadingOutlined /> :
              step.status === 'failed' ? <CloseCircleOutlined /> :
              <ClockCircleOutlined />,
            title: (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontWeight: 500 }}>
                  {ROLE_NAMES[step.role] || step.agent}
                </span>
                {step.confidence !== undefined && step.confidence > 0 && (
                  <Tag style={{ fontSize: 11, margin: 0 }}>
                    {(step.confidence * 100).toFixed(0)}% 置信
                  </Tag>
                )}
              </div>
            ),
            description: (
              <div style={{ marginTop: 4 }}>
                {step.thinking && step.status === 'running' && (
                  <Paragraph
                    type="secondary"
                    style={{
                      fontSize: 12,
                      fontFamily: 'monospace',
                      background: '#f5f5f5',
                      padding: '6px 10px',
                      borderRadius: 4,
                      marginBottom: 8,
                      whiteSpace: 'pre-wrap',
                      lineHeight: 1.5,
                    }}
                  >
                    {step.thinking}
                  </Paragraph>
                )}
                {step.status === 'completed' && (
                  <Text style={{ fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                    {step.content.length > 200
                      ? step.content.slice(0, 200) + '...'
                      : step.content
                    }
                  </Text>
                )}
                {step.status === 'running' && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    正在执行中...
                  </Text>
                )}
                {step.status === 'failed' && (
                  <Text type="danger" style={{ fontSize: 12 }}>
                    执行失败: {step.content}
                  </Text>
                )}
                <div style={{ marginTop: 4 }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {step.timestamp}
                  </Text>
                </div>
              </div>
            ),
          }))}
        />
      )}
    </Card>
  );
};

export default AgentThinkingPanel;
