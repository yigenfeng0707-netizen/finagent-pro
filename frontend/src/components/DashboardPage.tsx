import React from 'react';
import { Card, Row, Col, Statistic, Button, Input, Select, Skeleton, Tag } from 'antd';
import {
  RiseOutlined, FallOutlined, DollarOutlined, RobotOutlined, ThunderboltOutlined,
} from '@ant-design/icons';
import StockChart from '../charts/StockChart';
import PortfolioPieChart from '../charts/PortfolioPieChart';
import RiskGauge from '../charts/RiskGauge';
import LiveAgentFeed, { AgentFeedMessage } from './LiveAgentFeed';
import { HK_STOCKS } from '../constants';

const { Option } = Select;

export interface DashboardPageProps {
  marketOverview: {
    hsIndex: number;
    hsChange: number;
    techIndex: number;
    techChange: number;
    volume: number;
  };
  stockData: any;
  selectedStock: string;
  setSelectedStock: (s: string) => void;
  investmentAmount: number;
  setInvestmentAmount: (n: number) => void;
  riskPreference: string;
  setRiskPreference: (s: string) => void;
  runAnalysis: () => void;
  loading: boolean;
  feedMessages: any[];
  analysisResult: any;
  wsConnected: boolean;
  runDemo: () => void;
  analysisMetrics: {duration: number, toolCalls: number, agents: number} | null;
}

const DashboardPage: React.FC<DashboardPageProps> = ({
  marketOverview,
  stockData,
  selectedStock,
  setSelectedStock,
  investmentAmount,
  setInvestmentAmount,
  riskPreference,
  setRiskPreference,
  runAnalysis,
  loading,
  feedMessages,
  analysisResult,
  wsConnected,
  runDemo,
  analysisMetrics,
}) => (
  <div className="dashboard">
    <Row gutter={[16, 16]}>
      <Col span={6}>
        <Card><Statistic title="恒生指数" value={marketOverview.hsIndex} precision={2}
          valueStyle={{ color: marketOverview.hsChange >= 0 ? '#cf1322' : '#3f8600' }}
          prefix={marketOverview.hsChange >= 0 ? <RiseOutlined /> : <FallOutlined />}
          suffix={`${marketOverview.hsChange >= 0 ? '+' : ''}${marketOverview.hsChange.toFixed(2)}%`} />
        </Card>
      </Col>
      <Col span={6}>
        <Card><Statistic title="恒生科技指数" value={marketOverview.techIndex} precision={2}
          valueStyle={{ color: marketOverview.techChange >= 0 ? '#cf1322' : '#3f8600' }}
          prefix={marketOverview.techChange >= 0 ? <RiseOutlined /> : <FallOutlined />}
          suffix={`${marketOverview.techChange >= 0 ? '+' : ''}${marketOverview.techChange.toFixed(2)}%`} />
        </Card>
      </Col>
      <Col span={6}>
        <Card><Statistic title="今日成交额(亿)" value={marketOverview.volume} precision={0} prefix={<DollarOutlined />} /></Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic title="AI分析状态"
            value={loading ? '分析中' : (wsConnected ? '已连接' : '就绪')}
            valueStyle={{ color: loading ? '#faad14' : (wsConnected ? '#52c41a' : '#1890ff') }}
            prefix={<RobotOutlined />} />
        </Card>
      </Col>
    </Row>
    <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
      <Col span={16}>
        <Card title="股票走势" extra={
          <Select value={selectedStock} onChange={setSelectedStock} style={{ width: 150 }}>
            {HK_STOCKS.map(s => <Option key={s.code} value={s.code}>{s.name} ({s.code})</Option>)}
          </Select>
        }>
          {stockData ? <StockChart data={stockData} recommendation={analysisResult?.recommendation} /> : <div style={{ height: 400, padding: 24 }}><Skeleton active><Skeleton.Input active style={{ width: '100%', marginBottom: 16 }} /><Skeleton.Button active style={{ marginRight: 8 }} /><Skeleton.Button active /></Skeleton></div>}
        </Card>
      </Col>
      <Col span={8}>
        <Card title="快速分析">
          <div style={{ marginBottom: 16 }}>
            <label>投资金额 (HKD):</label>
            <Input type="number" value={investmentAmount} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setInvestmentAmount(Number(e.target.value))} prefix="$" style={{ marginTop: 8 }} />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label>风险偏好:</label>
            <Select value={riskPreference} onChange={setRiskPreference} style={{ width: '100%', marginTop: 8 }}>
              <Option value="conservative">保守型</Option>
              <Option value="moderate">稳健型</Option>
              <Option value="aggressive">进取型</Option>
            </Select>
          </div>
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={runAnalysis} loading={loading} block size="large">
            {loading ? 'AI分析中...' : '启动AI分析'}
          </Button>
          <Button type="primary" ghost icon={<ThunderboltOutlined />} onClick={runDemo} loading={loading} block size="large" style={{ marginTop: 8 }}>
            一键演示
          </Button>
          {loading && feedMessages.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <LiveAgentFeed messages={feedMessages as AgentFeedMessage[]} height={200} />
            </div>
          )}
        </Card>
      </Col>
    </Row>
    {analysisResult && (
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={8}>
          <Card title="投资组合配置"><PortfolioPieChart data={analysisResult.portfolio_allocation} /></Card>
        </Col>
        <Col span={8}>
          <Card title="风险等级评估"><RiskGauge value={analysisResult.risk_level} /></Card>
        </Col>
        <Col span={8}>
          <Card title="投资建议">
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <Tag color={analysisResult.recommendation === 'buy' ? 'red' : analysisResult.recommendation === 'sell' ? 'green' : 'default'}
                style={{ fontSize: 18, padding: '8px 16px' }}>
                {analysisResult.recommendation === 'buy' ? '买入' : analysisResult.recommendation === 'sell' ? '卖出' : '持有'}
              </Tag>
              <div style={{ marginTop: 16 }}>
                <Statistic title="预期收益率" value={analysisResult.expected_return} precision={2} suffix="%"
                  valueStyle={{ color: analysisResult.expected_return >= 0 ? '#cf1322' : '#3f8600' }} />
              </div>
              <div style={{ marginTop: 16 }}>
                <Statistic title="置信度" value={analysisResult.confidence} precision={1} suffix="%" />
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    )}
  </div>
);

export default DashboardPage;
