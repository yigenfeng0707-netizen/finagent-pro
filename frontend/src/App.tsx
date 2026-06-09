import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Layout, Menu, Card, Row, Col, Statistic, Button, Input, Select, message, Tabs, List, Tag, Spin } from 'antd';
import {
  DashboardOutlined, LineChartOutlined, PieChartOutlined, SafetyOutlined,
  RobotOutlined, SettingOutlined, ThunderboltOutlined, RiseOutlined,
  FallOutlined, DollarOutlined, ApiOutlined,
} from '@ant-design/icons';
import StockChart from './charts/StockChart';
import PortfolioPieChart from './charts/PortfolioPieChart';
import RiskGauge from './charts/RiskGauge';
import LiveAgentFeed, { AgentFeedMessage } from './components/LiveAgentFeed';
import AgentThinkingPanel, { ThinkingStep } from './components/AgentThinkingPanel';
import OrchestratorWorkbench from './components/OrchestratorWorkbench';
import { useWebSocket, WSMessage } from './hooks/useWebSocket';
import './App.css';

const { Header, Sider, Content } = Layout;
const { Option } = Select;

const API_BASE = process.env.REACT_APP_API_URL || '';

const HK_STOCKS = [
  { code: '00700', name: '腾讯控股', sector: '科技' },
  { code: '09988', name: '阿里巴巴', sector: '科技' },
  { code: '03690', name: '美团', sector: '科技' },
  { code: '01810', name: '小米集团', sector: '科技' },
  { code: '01299', name: '友邦保险', sector: '金融' },
  { code: '02318', name: '中国平安', sector: '金融' },
  { code: '00883', name: '中国海洋石油', sector: '能源' },
  { code: '00941', name: '中国移动', sector: '通信' },
];

interface StockData {
  dates: string[]; prices: number[]; volumes: number[];
  ma5?: number[]; ma20?: number[]; ma60?: number[];
}

interface AgentMessage {
  agent: string; role: string; content: string; timestamp: string;
  status?: string; confidence?: number; thinking?: string; data?: any;
}

interface AnalysisResult {
  recommendation: string; confidence: number; risk_level: number;
  expected_return: number; reasoning: string;
  portfolio_allocation: Array<{symbol: string; name: string; weight: number; amount: number}>;
  agent_messages: AgentMessage[];
}

function genId() { return 'sess_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }

const App: React.FC = () => {
  const [collapsed] = useState(false);
  const [selectedMenu, setSelectedMenu] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  const [stockData, setStockData] = useState<StockData | null>(null);
  const [selectedStock, setSelectedStock] = useState('00700');
  const [investmentAmount, setInvestmentAmount] = useState<number>(100000);
  const [riskPreference, setRiskPreference] = useState('moderate');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const [feedMessages, setFeedMessages] = useState<AgentFeedMessage[]>([]);
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([]);
  const [wsConnected, setWsConnected] = useState(false);

  const [workbenchSteps, setWorkbenchSteps] = useState<any[]>([]);
  const [toolCalls, setToolCalls] = useState<any[]>([]);
  const [liveContext, setLiveContext] = useState<Record<string, string>>({});

  const stepCounter = useRef(0);

  const handleWSMessage = useCallback((msg: WSMessage) => {
    if (msg.type === 'agent_progress') {
      const p = msg.payload;
      const feed: AgentFeedMessage = {
        agent: p.agent || '', role: p.role || '', content: p.content || '',
        status: p.status || 'completed', timestamp: p.timestamp || '',
        confidence: p.confidence, thinking: p.thinking,
      };
      setFeedMessages(prev => [...prev, feed]);

      setThinkingSteps(prev => {
        const role = p.role || '';
        const existingIdx = prev.findIndex(s => s.role === role && s.status === 'running');
        if (existingIdx >= 0) {
          const updated = [...prev];
          updated[existingIdx] = {
            ...updated[existingIdx],
            status: p.status || 'completed',
            content: p.content || '',
            thinking: p.thinking || undefined,
            confidence: p.confidence,
            data: p.data,
          };
          return updated;
        }
        if (p.status === 'running' || !prev.find(s => s.role === role)) {
          stepCounter.current += 1;
          return [...prev, {
            stepId: stepCounter.current,
            agent: p.agent || '',
            role,
            content: p.content || '',
            thinking: p.thinking,
            status: p.status || 'completed',
            timestamp: p.timestamp || '',
            confidence: p.confidence,
            data: p.data,
          }];
        }
        return prev;
      });

      if (p.thinking) {
        setWorkbenchSteps(prev => {
          const role = p.role || '';
          const exists = prev.find((s: any) => s.role === role);
          if (exists) return prev.map((s: any) => s.role === role ? { ...s, status: p.status || 'completed' } : s);
          return [...prev, {
            stepId: stepCounter.current,
            agent: p.agent || '',
            role,
            description: `${p.agent || ''} 正在执行...`,
            status: p.status || 'running',
            dependsOn: [],
            inputKeys: [],
            outputKey: role + '_analysis',
          }];
        });
      }

      if (p.data) {
        setLiveContext(prev => ({ ...prev, [p.role + '_analysis']: JSON.stringify(p.data).slice(0, 200) }));
      }
    } else if (msg.type === 'final_report') {
      const report = msg.payload;
      setAnalysisResult(report);
      setLoading(false);
      message.success('多Agent分析完成！');
    }
  }, []);

  const wsHandler = useWebSocket(sessionId, {
    onMessage: handleWSMessage,
    onConnect: () => setWsConnected(true),
    onDisconnect: () => setWsConnected(false),
    enabled: !!sessionId && loading,
  });

  useEffect(() => {
    if (sessionId && !loading) {
      wsHandler.disconnect();
    }
  }, [loading, sessionId, wsHandler]);

  const fetchStockData = async (symbol: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/market/stock/${symbol}?market=hk&days=180`);
      const data = await response.json();
      if (data.status === 'success') setStockData(data.data);
    } catch { message.error('获取股票数据失败'); }
  };

  const runAnalysis = async () => {
    setLoading(true);
    setAnalysisResult(null);
    setFeedMessages([]);
    setThinkingSteps([]);
    setWorkbenchSteps([]);
    setToolCalls([]);
    setLiveContext({});
    stepCounter.current = 0;

    const sid = genId();
    setSessionId(sid);

    try {
      if (!wsConnected) {
        await new Promise(r => setTimeout(r, 500));
      }

      stepCounter.current += 1;
      const planStep: ThinkingStep = {
        stepId: stepCounter.current,
        agent: '编排器',
        role: 'orchestrator',
        content: '规划完成: 共4个步骤 → 市场分析→情绪扫描→风险评估→组合建议',
        status: 'completed',
        timestamp: new Date().toLocaleTimeString(),
      };
      setFeedMessages([planStep]);
      setThinkingSteps([planStep]);
      setWorkbenchSteps([{
        stepId: stepCounter.current, agent: '编排器', role: 'orchestrator',
        description: '规划完成: 共4个步骤 → 市场分析→情绪扫描→风险评估→组合建议',
        status: 'completed', dependsOn: [], inputKeys: [], outputKey: 'plan',
      }]);

      const response = await fetch(`${API_BASE}/api/orchestrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbols: [selectedStock],
          investment_amount: investmentAmount,
          risk_preference: riskPreference,
          market: 'hk',
          session_id: sid,
        }),
      });
      const result = await response.json();
      if (result.status === 'success') {
        setAnalysisResult(result.data);
        message.success('分析完成！');
      } else {
        message.error(result.error || '分析失败');
      }
    } catch {
      message.error('分析失败，请稍后重试');
    } finally {
      setLoading(false);
      setSessionId(null);
    }
  };

  const fetchMarketOverview = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/market/hot?market=hk`);
      const data = await response.json();
      if (data.status === 'success') {
        setMarketOverview({
          hsIndex: 18500 + Math.random() * 500,
          hsChange: (Math.random() - 0.5) * 2,
          techIndex: 4200 + Math.random() * 200,
          techChange: (Math.random() - 0.5) * 3,
          volume: 1200 + Math.random() * 300,
        });
      }
    } catch { console.error('获取市场概览失败'); }
  };

  const [marketOverview, setMarketOverview] = useState({
    hsIndex: 0, hsChange: 0, techIndex: 0, techChange: 0, volume: 0,
  });

  useEffect(() => {
    fetchStockData(selectedStock);
    fetchMarketOverview();
    const interval = setInterval(fetchMarketOverview, 30000);
    return () => clearInterval(interval);
  }, [selectedStock]);

  const renderDashboard = () => (
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
            {stockData ? <StockChart data={stockData} /> : <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Spin size="large" /></div>}
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
    </div>
  );

  const renderAgentChat = () => (
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

  const renderWorkbench = () => (
    <OrchestratorWorkbench
      steps={workbenchSteps}
      toolCalls={toolCalls}
      liveContext={liveContext}
    />
  );

  const renderStockList = () => (
    <Card title="港股热门股票">
      <List grid={{ gutter: 16, column: 4 }} dataSource={HK_STOCKS}
        renderItem={(stock: typeof HK_STOCKS[0]) => (
          <List.Item>
            <Card hoverable onClick={() => setSelectedStock(stock.code)}
              style={{ borderColor: selectedStock === stock.code ? '#1890ff' : undefined }}>
              <div style={{ textAlign: 'center' }}>
                <h4>{stock.name}</h4>
                <p style={{ color: '#666' }}>{stock.code}</p>
                <Tag>{stock.sector}</Tag>
              </div>
            </Card>
          </List.Item>
        )} />
    </Card>
  );

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed}>
        <div className="logo">
          <RobotOutlined style={{ fontSize: 24, color: 'white' }} />
          {!collapsed && <span style={{ color: 'white', marginLeft: 8, fontSize: 18 }}>FinAgent Pro</span>}
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={[selectedMenu]} onClick={({ key }: { key: string }) => setSelectedMenu(key)}
          items={[
            { key: 'dashboard', icon: <DashboardOutlined />, label: '投资仪表盘' },
            { key: 'stocks', icon: <LineChartOutlined />, label: '港股行情' },
            { key: 'agents', icon: <RobotOutlined />, label: 'Agent对话' },
            { key: 'workbench', icon: <ApiOutlined />, label: '数字员工工作台' },
            { key: 'portfolio', icon: <PieChartOutlined />, label: '组合分析' },
            { key: 'risk', icon: <SafetyOutlined />, label: '风险评估' },
            { key: 'settings', icon: <SettingOutlined />, label: '系统设置' },
          ]} />
      </Sider>
      <Layout>
        <Header style={{ padding: '0 24px', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h2 style={{ margin: 0 }}>
            {selectedMenu === 'dashboard' && '投资仪表盘'}
            {selectedMenu === 'stocks' && '港股行情'}
            {selectedMenu === 'agents' && '多Agent协作'}
            {selectedMenu === 'workbench' && '数字员工工作台'}
            {selectedMenu === 'portfolio' && '组合分析'}
            {selectedMenu === 'risk' && '风险评估'}
            {selectedMenu === 'settings' && '系统设置'}
          </h2>
          <div>
            <Tag color="blue">港股通</Tag>
            <Tag color="green">AI驱动</Tag>
            <Tag color="orange">国产大模型</Tag>
          </div>
        </Header>
        <Content style={{ margin: '24px 16px', padding: 24, background: '#f0f2f5', minHeight: 280 }}>
          {selectedMenu === 'dashboard' && renderDashboard()}
          {selectedMenu === 'stocks' && renderStockList()}
          {selectedMenu === 'agents' && renderAgentChat()}
          {selectedMenu === 'workbench' && renderWorkbench()}
          {selectedMenu === 'portfolio' && (
            <Card title="投资组合分析">
              {analysisResult ? (
                <Tabs defaultActiveKey="1"
                  items={[
                    { key: '1', label: '配置详情',
                      children: <List dataSource={analysisResult.portfolio_allocation}
                        renderItem={(item: any) => (
                          <List.Item>
                            <List.Item.Meta title={`${item.name} (${item.symbol})`}
                              description={`配置金额: HKD ${item.amount.toLocaleString()}`} />
                            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{item.weight}%</div>
                          </List.Item>
                        )} />
                    },
                    { key: '2', label: '分析报告',
                      children: <div style={{ whiteSpace: 'pre-wrap', lineHeight: 2 }}>{analysisResult.reasoning}</div>
                    },
                  ]}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: '100px 0', color: '#999' }}>
                  <PieChartOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                  <p>请先执行投资分析</p>
                </div>
              )}
            </Card>
          )}
          {selectedMenu === 'risk' && (
            <Card title="风险评估中心">
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Card title="当前组合风险">
                    {analysisResult ? <RiskGauge value={analysisResult.risk_level} height={350} />
                      : <div style={{ height: 350, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>暂无分析数据</div>}
                  </Card>
                </Col>
                <Col span={12}>
                  <Card title="风险等级说明">
                    <List>
                      <List.Item><Tag color="green">低风险 (0-30)</Tag><span>适合保守型投资者，追求本金安全</span></List.Item>
                      <List.Item><Tag color="yellow">中低风险 (30-50)</Tag><span>适合稳健型投资者，平衡收益与风险</span></List.Item>
                      <List.Item><Tag color="orange">中风险 (50-70)</Tag><span>适合平衡型投资者，可接受一定波动</span></List.Item>
                      <List.Item><Tag color="red">高风险 (70-100)</Tag><span>适合进取型投资者，追求高收益</span></List.Item>
                    </List>
                  </Card>
                </Col>
              </Row>
            </Card>
          )}
          {selectedMenu === 'settings' && (
            <Card title="系统配置">
              <p>大模型: DeepSeek V3 (deepseek-chat)</p>
              <p>备选模型: 智谱 GLM-4-plus</p>
              <p>数据源: AKShare</p>
              <p>向量数据库: ChromaDB</p>
              <p>编排引擎: Agent Orchestrator</p>
              <p>版本: v2.0.0</p>
              <p>WebSocket: {wsConnected ? <Tag color="success">已连接</Tag> : <Tag color="default">未连接</Tag>}</p>
            </Card>
          )}
        </Content>
      </Layout>
    </Layout>
  );
};

export default App;
