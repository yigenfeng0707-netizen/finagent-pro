import React from 'react';
import { Card, Row, Col, Statistic, Button, Input, Select, Skeleton, Tag, Steps, Progress, Alert } from 'antd';
import { Typography } from 'antd';
import {
  RiseOutlined, FallOutlined, DollarOutlined, RobotOutlined, ThunderboltOutlined,
} from '@ant-design/icons';
import StockChart from '../charts/StockChart';
import PortfolioPieChart from '../charts/PortfolioPieChart';
import RiskGauge from '../charts/RiskGauge';
import LiveAgentFeed from './LiveAgentFeed';
import { HK_STOCKS } from '../constants';
import { useAppStore } from '../stores/appStore';
import { useAnalysis } from '../hooks/useAnalysis';

const { Option } = Select;
const { Title } = Typography;

const DashboardPage: React.FC = () => {
  const marketOverview = useAppStore(s => s.marketOverview);
  const stockData = useAppStore(s => s.stockData);
  const selectedStock = useAppStore(s => s.selectedStock);
  const setSelectedStock = useAppStore(s => s.setSelectedStock);
  const investmentAmount = useAppStore(s => s.investmentAmount);
  const setInvestmentAmount = useAppStore(s => s.setInvestmentAmount);
  const riskPreference = useAppStore(s => s.riskPreference);
  const setRiskPreference = useAppStore(s => s.setRiskPreference);
  const loading = useAppStore(s => s.loading);
  const feedMessages = useAppStore(s => s.feedMessages);
  const analysisResult = useAppStore(s => s.analysisResult);
  const wsConnected = useAppStore(s => s.wsConnected);
  const analysisMetrics = useAppStore(s => s.analysisMetrics);
  const analysisProgress = useAppStore(s => s.analysisProgress);

  const { runAnalysis, runDemo } = useAnalysis();

  return (
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
            {stockData ? <StockChart data={stockData} recommendation={analysisResult?.recommendation} /> : <div style={{ height: 400, padding: 24 }}><Skeleton active /></div>}
          </Card>
        </Col>
        <Col span={8}>
          <Card title="快速分析">
            <div style={{ marginBottom: 16 }}>
              <label htmlFor="investment-amount">投资金额 (HKD):</label>
              <Input id="investment-amount" type="number" value={investmentAmount} onChange={(e) => setInvestmentAmount(Number(e.target.value))} prefix="$" style={{ marginTop: 8 }} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label htmlFor="risk-preference">风险偏好:</label>
              <Select id="risk-preference" value={riskPreference} onChange={setRiskPreference} style={{ width: '100%', marginTop: 8 }}>
                <Option value="conservative">保守型</Option>
                <Option value="moderate">稳健型</Option>
                <Option value="aggressive">进取型</Option>
              </Select>
            </div>
            <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => runAnalysis()} loading={loading} block size="large">
              {loading ? 'AI分析中...' : '启动AI分析'}
            </Button>
            <Button type="primary" ghost icon={<ThunderboltOutlined />} onClick={runDemo} loading={loading} block size="large" style={{ marginTop: 8 }}>
              一键演示
            </Button>
            {loading && feedMessages.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <LiveAgentFeed messages={feedMessages} height={200} />
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

      {/* 分析进度弹窗 */}
      {loading && (
        <div role="alert" aria-live="assertive" aria-busy="true" style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.45)', zIndex: 1000,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        }}>
          <Card style={{ width: 480, borderRadius: 12, textAlign: 'center' }} bordered={false}>
            <Title level={4} style={{ marginBottom: 24 }}>AI 多Agent协作分析中</Title>
            <Steps
              current={analysisProgress.step - 1}
              status={analysisProgress.step > 0 ? 'process' : 'wait'}
              items={[
                { title: '市场分析师', description: '技术面分析' },
                { title: '情绪扫描器', description: '市场情绪' },
                { title: '风险经理', description: '风险评估' },
                { title: '组合顾问', description: '资产配置' },
              ]}
            />
            <Progress
              percent={Math.round((analysisProgress.step / 4) * 100)}
              status={analysisProgress.step >= 4 ? 'success' : 'active'}
              style={{ marginTop: 24 }}
            />
            <div style={{ marginTop: 12, color: '#888' }}>
              {analysisProgress.agentName ? `正在执行: ${analysisProgress.agentName}` : '正在初始化...'}
            </div>
          </Card>
        </div>
      )}

      {analysisMetrics && (
        <Alert
          type="success"
          showIcon
          message={`分析完成 | 耗时 ${analysisMetrics.duration.toFixed(1)}秒 | ${analysisMetrics.toolCalls}次工具调用 | ${analysisMetrics.agents}个Agent协作`}
          closable
          style={{ marginTop: 12 }}
        />
      )}
    </div>
  );
};

export default DashboardPage;
