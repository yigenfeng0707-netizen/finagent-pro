import React from 'react';
import { Card, Row, Col, Tag, Typography, Table, Empty, Descriptions } from 'antd';
import {
  BranchesOutlined, ToolOutlined, SwapOutlined, CheckCircleOutlined,
  LoadingOutlined, ClockCircleOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

interface PlanStep {
  stepId: number;
  agent: string;
  role: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  dependsOn: number[];
  inputKeys: string[];
  outputKey: string;
}

interface ToolCall {
  agent: string;
  tool: string;
  args: string;
  result: string;
  timestamp: string;
}

interface OrchestratorWorkbenchProps {
  steps: PlanStep[];
  toolCalls: ToolCall[];
  liveContext: Record<string, string>;
}

const ROLE_COLORS: Record<string, string> = {
  market_analyst: '#1890ff',
  sentiment_scanner: '#faad14',
  risk_manager: '#ff4d4f',
  portfolio_advisor: '#52c41a',
  orchestrator: '#722ed1',
};

const OrchestratorWorkbench: React.FC<OrchestratorWorkbenchProps> = ({
  steps, toolCalls, liveContext,
}) => {
  const flowColumns = [
    {
      title: '步骤',
      dataIndex: 'stepId',
      key: 'stepId',
      width: 60,
      render: (id: number) => <Text strong>{id}</Text>,
    },
    {
      title: 'Agent',
      dataIndex: 'agent',
      key: 'agent',
      width: 120,
      render: (_: string, row: PlanStep) => (
        <Tag color={ROLE_COLORS[row.role] || 'default'}>
          {row.agent}
        </Tag>
      ),
    },
    {
      title: '任务描述',
      dataIndex: 'description',
      key: 'description',
      render: (desc: string) => <Text style={{ fontSize: 13 }}>{desc}</Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (st: string) => {
        const map: Record<string, [React.ReactNode, string]> = {
          completed: [<CheckCircleOutlined />, 'success'],
          running: [<LoadingOutlined />, 'processing'],
          pending: [<ClockCircleOutlined />, 'default'],
          failed: [<Tag color="error">失败</Tag>, 'error'],
        };
        const [icon, color] = map[st] || [<ClockCircleOutlined />, 'default'];
        return <Tag icon={icon as React.ReactElement} color={color}>{st === 'completed' ? '完成' : st === 'running' ? '执行中' : st === 'failed' ? '失败' : '等待'}</Tag>;
      },
    },
    {
      title: '依赖',
      dataIndex: 'dependsOn',
      key: 'dependsOn',
      width: 100,
      render: (deps: number[]) => (
        deps.length ? deps.map(d => <Tag key={d} style={{ margin: 2 }}>步骤{d}</Tag>) : <Text type="secondary">-</Text>
      ),
    },
    {
      title: '输出',
      dataIndex: 'outputKey',
      key: 'outputKey',
      width: 120,
      render: (key: string) => key ? <Text code style={{ fontSize: 11 }}>{key}</Text> : null,
    },
  ];

  const toolColumns = [
    {
      title: 'Agent',
      dataIndex: 'agent',
      key: 'agent',
      width: 100,
      render: (a: string) => <Tag>{a}</Tag>,
    },
    {
      title: '工具',
      dataIndex: 'tool',
      key: 'tool',
      width: 160,
      render: (t: string) => <Text code style={{ fontSize: 11 }}>{t}</Text>,
    },
    {
      title: '参数',
      dataIndex: 'args',
      key: 'args',
      ellipsis: true,
      render: (a: string) => <Text style={{ fontSize: 12 }}>{a}</Text>,
    },
    {
      title: '结果摘要',
      dataIndex: 'result',
      key: 'result',
      ellipsis: true,
      render: (r: string) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {r && r.length > 60 ? r.slice(0, 60) + '...' : r}
        </Text>
      ),
    },
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 80,
      render: (t: string) => <Text type="secondary" style={{ fontSize: 11 }}>{t}</Text>,
    },
  ];

  return (
    <div style={{ height: '100%' }}>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card
            title={<span><BranchesOutlined /> 任务流程</span>}
            size="small"
          >
            <Table
              dataSource={steps}
              columns={flowColumns}
              rowKey="stepId"
              pagination={false}
              size="small"
              locale={{ emptyText: <Empty description="暂无任务" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
            />
          </Card>
        </Col>

        <Col span={24}>
          <Card
            title={<span><ToolOutlined /> 工具调用日志</span>}
            size="small"
          >
            <Table
              dataSource={toolCalls}
              columns={toolColumns}
              rowKey={(_: unknown, idx: number) => String(idx)}
              pagination={false}
              size="small"
              locale={{ emptyText: <Empty description="暂无工具调用" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
            />
          </Card>
        </Col>

        {Object.keys(liveContext).length > 0 && (
          <Col span={24}>
            <Card
              title={<span><SwapOutlined /> 上下文传递</span>}
              size="small"
            >
              <Descriptions column={1} size="small" bordered>
                {Object.entries(liveContext).map(([key, val]) => (
                  <Descriptions.Item key={key} label={<Text code>{key}</Text>}>
                    <Text ellipsis style={{ maxWidth: 600, display: 'inline-block' }}>
                      {val && val.length > 150 ? val.slice(0, 150) + '...' : val || '-'}
                    </Text>
                  </Descriptions.Item>
                ))}
              </Descriptions>
            </Card>
          </Col>
        )}
      </Row>
    </div>
  );
};

export default OrchestratorWorkbench;
