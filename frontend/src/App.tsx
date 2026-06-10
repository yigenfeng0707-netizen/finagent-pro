import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Layout, Menu, Card, Row, Col, Tabs, List, Tag, message } from 'antd';
import {
  DashboardOutlined, LineChartOutlined, PieChartOutlined, SafetyOutlined,
  RobotOutlined, SettingOutlined, ApiOutlined,
} from '@ant-design/icons';
import { AgentFeedMessage } from './components/LiveAgentFeed';
import { ThinkingStep } from './components/AgentThinkingPanel';
import OrchestratorWorkbench from './components/OrchestratorWorkbench';
import DashboardPage from './components/DashboardPage';
import AgentChatPage from './components/AgentChatPage';
import StockListPage from './components/StockListPage';
import RiskGauge from './charts/RiskGauge';
import { useWebSocket, WSMessage } from './hooks/useWebSocket';
import { API_BASE } from './constants';
import './App.css';

const { Header, Sider, Content } = Layout;

const MENU_TITLES: Record<string, string> = {
  dashboard: '投资仪表盘',
  stocks: '港股行情',
  agents: '多Agent协作',
  workbench: '数字员工工作台',
  portfolio: '组合分析',
  risk: '风险评估',
  settings: '系统设置',
};

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
  const [collapsed, setCollapsed] = useState(false);
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

      // Extract tool calls from agent data
      if (p.data && p.role !== 'orchestrator') {
        const toolEntries: any[] = [];
        if (p.data.current_price !== undefined) {
          toolEntries.push({
            agent: p.agent, tool: 'get_stock_price',
            args: `symbol=${selectedStock}`, result: `价格: ${p.data.current_price} HKD`,
            timestamp: p.timestamp || new Date().toLocaleTimeString(),
          });
        }
        if (p.data.rsi !== undefined) {
          toolEntries.push({
            agent: p.agent, tool: 'get_technical_indicators',
            args: `symbol=${selectedStock}`, result: `RSI: ${p.data.rsi}, MA5: ${p.data.ma5 || 'N/A'}`,
            timestamp: p.timestamp || new Date().toLocaleTimeString(),
          });
        }
        if (p.data.risk_data) {
          toolEntries.push({
            agent: p.agent, tool: 'get_portfolio_risk',
            args: `symbols=${selectedStock}`, 
            result: `波动率: ${p.data.risk_data?.portfolio_volatility || 'N/A'}%`,
            timestamp: p.timestamp || new Date().toLocaleTimeString(),
          });
        }
        if (toolEntries.length > 0) {
          setToolCalls(prev => [...prev, ...toolEntries]);
        }
      }
    } else if (msg.type === 'final_report') {
      const report = msg.payload;
      setAnalysisResult(report);
      setLoading(false);
      message.success('多Agent分析完成！');
      // Small delay to ensure all messages are rendered, then disconnect
      setTimeout(() => {
        setSessionId(null);
      }, 2000);
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
      // Wait for WebSocket to connect (with timeout)
      const wsReady = await new Promise<boolean>((resolve) => {
        if (wsConnected) { resolve(true); return; }
        const checkInterval = setInterval(() => {
          if (wsConnected) { clearInterval(checkInterval); resolve(true); }
        }, 100);
        setTimeout(() => { clearInterval(checkInterval); resolve(false); }, 3000);
      });

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
      if (result.status === 'error') {
        message.error(result.error || '分析失败');
        setLoading(false);
        setSessionId(null);
      } else if (!wsReady) {
        // WebSocket not available, use HTTP response as fallback
        setAnalysisResult(result.data);
        message.success('分析完成！');
        setLoading(false);
        setSessionId(null);
      }
      // If wsReady and status success, wait for WebSocket final_report to set result
    } catch {
      message.error('分析失败，请稍后重试');
      setLoading(false);
      setSessionId(null);
    }
  };

  const fetchMarketOverview = async () => {
    try {
      // selectedStock is available from closure for potential stock-specific filtering
      const symbol = selectedStock;
      const response = await fetch(`${API_BASE}/api/market/hk-spot`);
      const data = await response.json();
      if (data.success && data.data && data.data.length > 0) {
        // Calculate index-like metrics from top stocks
        const stocks = data.data;
        const avgChange = stocks.reduce((sum: number, s: any) => sum + (s.change_pct || 0), 0) / stocks.length;
        const totalVolume = stocks.reduce((sum: number, s: any) => sum + (s.turnover || 0), 0);
        setMarketOverview({
          hsIndex: 18500 + avgChange * 100,  // Base + weighted change
          hsChange: avgChange,
          techIndex: 4200 + avgChange * 50,
          techChange: avgChange * 1.2,
          volume: Math.round(totalVolume / 100000000),  // Convert to 亿
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

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed} onCollapse={(c: boolean) => setCollapsed(c)}>
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
            {MENU_TITLES[selectedMenu] || ''}
          </h2>
          <div>
            <Tag color="blue">港股通</Tag>
            <Tag color="green">AI驱动</Tag>
            <Tag color="orange">国产大模型</Tag>
          </div>
        </Header>
        <Content style={{ margin: '24px 16px', padding: 24, background: '#f0f2f5', minHeight: 280 }}>
          {selectedMenu === 'dashboard' && (
            <DashboardPage
              marketOverview={marketOverview}
              stockData={stockData}
              selectedStock={selectedStock}
              setSelectedStock={setSelectedStock}
              investmentAmount={investmentAmount}
              setInvestmentAmount={setInvestmentAmount}
              riskPreference={riskPreference}
              setRiskPreference={setRiskPreference}
              runAnalysis={runAnalysis}
              loading={loading}
              feedMessages={feedMessages}
              analysisResult={analysisResult}
              wsConnected={wsConnected}
            />
          )}
          {selectedMenu === 'stocks' && (
            <StockListPage
              selectedStock={selectedStock}
              setSelectedStock={setSelectedStock}
            />
          )}
          {selectedMenu === 'agents' && (
            <AgentChatPage
              feedMessages={feedMessages}
              thinkingSteps={thinkingSteps}
            />
          )}
          {selectedMenu === 'workbench' && (
            <OrchestratorWorkbench
              steps={workbenchSteps}
              toolCalls={toolCalls}
              liveContext={liveContext}
            />
          )}
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
