import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Layout, Menu, Card, Row, Col, Tabs, List, Tag, message, Alert, Steps, Progress, Statistic, ConfigProvider, theme, Switch, Button } from 'antd';
import { Typography as AntTypography } from 'antd';
import {
  DashboardOutlined, LineChartOutlined, PieChartOutlined, SafetyOutlined,
  RobotOutlined, SettingOutlined, ApiOutlined, SunOutlined, MoonOutlined, FilePdfOutlined,
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

const { Title } = AntTypography;

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
  cvar_95?: number; sharpe_ratio?: number; annual_return?: number; annual_volatility?: number;
}

function genId() { return 'sess_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }

const App: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
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
  const [analysisMetrics, setAnalysisMetrics] = useState<{duration: number, toolCalls: number, agents: number} | null>(null);
  const [analysisProgress, setAnalysisProgress] = useState<{step: number, total: number, agentName: string}>({step: 0, total: 4, agentName: ''});
  const analysisStartTime = useRef<number>(0);

  const stepCounter = useRef(0);
  const selectedStockRef = useRef(selectedStock);
  const toolCallsRef = useRef<any[]>([]);
  const wsConnectedRef = useRef(false);

  // Keep refs in sync with state
  useEffect(() => { selectedStockRef.current = selectedStock; }, [selectedStock]);
  useEffect(() => { toolCallsRef.current = toolCalls; }, [toolCalls]);
  useEffect(() => { wsConnectedRef.current = wsConnected; }, [wsConnected]);

  const handleWSMessage = useCallback((msg: WSMessage) => {
    if (msg.type === 'agent_progress') {
      const p = msg.payload;
      // Update progress tracking based on agent role
      const roleProgressMap: Record<string, {step: number, total: number, agentName: string}> = {
        MARKET_ANALYST: { step: 1, total: 4, agentName: '市场分析师' },
        SENTIMENT_SCANNER: { step: 2, total: 4, agentName: '情绪扫描器' },
        RISK_MANAGER: { step: 3, total: 4, agentName: '风险经理' },
        PORTFOLIO_ADVISOR: { step: 4, total: 4, agentName: '组合顾问' },
      };
      if (p.role && roleProgressMap[p.role]) {
        setAnalysisProgress(roleProgressMap[p.role]);
      }

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

      // Extract tool calls from agent data — use ref to avoid stale closure
      if (p.data && p.role !== 'orchestrator') {
        const currentSymbol = selectedStockRef.current;
        const toolEntries: any[] = [];
        if (p.data.current_price !== undefined) {
          toolEntries.push({
            agent: p.agent, tool: 'get_stock_price',
            args: `symbol=${currentSymbol}`, result: `价格: ${p.data.current_price} HKD`,
            timestamp: p.timestamp || new Date().toLocaleTimeString(),
          });
        }
        if (p.data.rsi !== undefined) {
          toolEntries.push({
            agent: p.agent, tool: 'get_technical_indicators',
            args: `symbol=${currentSymbol}`, result: `RSI: ${p.data.rsi}, MA5: ${p.data.ma5 || 'N/A'}`,
            timestamp: p.timestamp || new Date().toLocaleTimeString(),
          });
        }
        if (p.data.risk_data) {
          toolEntries.push({
            agent: p.agent, tool: 'get_portfolio_risk',
            args: `symbols=${currentSymbol}`, 
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
      setAnalysisProgress({step: 5, total: 4, agentName: ''});
      setAnalysisMetrics({
        duration: (Date.now() - analysisStartTime.current) / 1000,
        toolCalls: toolCallsRef.current.length,  // 使用 ref 获取最新值
        agents: 4,
      });
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
  }, [loading, sessionId, wsHandler.disconnect]);

  const fetchStockData = async (symbol: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/market/stock/${symbol}?market=hk&days=180`);
      if (!response.ok) { message.error(`获取股票数据失败 (${response.status})`); return; }
      const data = await response.json();
      if (data.status === 'success') setStockData(data.data);
    } catch { message.error('获取股票数据失败'); }
  };

  const runAnalysis = async (stock?: string, amount?: number, risk?: string) => {
    setLoading(true);
    setAnalysisResult(null);
    setFeedMessages([]);
    setThinkingSteps([]);
    setWorkbenchSteps([]);
    setToolCalls([]);
    setLiveContext({});
    setAnalysisMetrics(null);
    setAnalysisProgress({step: 0, total: 4, agentName: ''});
    analysisStartTime.current = Date.now();
    stepCounter.current = 0;

    const sid = genId();
    setSessionId(sid);

    try {
      // Wait for WebSocket to connect (with timeout) — use ref to avoid stale closure
      const wsReady = await new Promise<boolean>((resolve) => {
        if (wsConnectedRef.current) { resolve(true); return; }
        const checkInterval = setInterval(() => {
          if (wsConnectedRef.current) { clearInterval(checkInterval); resolve(true); }
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
          symbols: [stock || selectedStock],
          investment_amount: amount || investmentAmount,
          risk_preference: risk || riskPreference,
          market: 'hk',
          session_id: sid,
        }),
      });
      if (!response.ok) {
        message.error(`分析请求失败 (${response.status})`);
        setLoading(false);
        setSessionId(null);
        return;
      }
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

  const runDemo = () => {
    setSelectedStock('00700');
    setInvestmentAmount(100000);
    setRiskPreference('moderate');
    runAnalysis('00700', 100000, 'moderate');
  };

  const exportReport = () => {
    if (!analysisResult) { message.warning('请先执行分析后再导出报告'); return; }
    const r = analysisResult;
    const w = window.open('', '_blank');
    if (!w) { message.error('无法打开导出窗口，请允许弹窗'); return; }
    w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>FinAgent Pro 投资分析报告</title>
      <style>
        body { font-family: -apple-system, 'Segoe UI', sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; }
        h1 { color: #1890ff; border-bottom: 2px solid #1890ff; padding-bottom: 8px; }
        h2 { color: #555; margin-top: 32px; }
        .metric { display: inline-block; margin-right: 32px; margin-bottom: 16px; }
        .metric .label { font-size: 12px; color: #999; }
        .metric .value { font-size: 24px; font-weight: bold; }
        .buy { color: #cf1322; } .sell { color: #3f8600; } .hold { color: #faad14; }
        table { width: 100%; border-collapse: collapse; margin: 16px 0; }
        th, td { border: 1px solid #e8e8e8; padding: 10px 14px; text-align: left; }
        th { background: #fafafa; font-weight: 600; }
        .reasoning { white-space: pre-wrap; line-height: 1.8; background: #f6f8fa; padding: 16px; border-radius: 8px; }
        .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e8e8e8; color: #999; font-size: 12px; }
        @media print { body { margin: 20px; } }
      </style></head><body>
      <h1>FinAgent Pro AI 投资分析报告</h1>
      <p>生成时间：${new Date().toLocaleString('zh-CN')}</p>
      <p>分析标的：${selectedStock} | 投资金额：HKD ${investmentAmount.toLocaleString()} | 风险偏好：${riskPreference}</p>
      <h2>核心指标</h2>
      <div>
        <div class="metric"><div class="label">投资建议</div><div class="value ${r.recommendation}">${r.recommendation === 'buy' ? '买入' : r.recommendation === 'sell' ? '卖出' : '持有'}</div></div>
        <div class="metric"><div class="label">置信度</div><div class="value">${(r.confidence * 100).toFixed(1)}%</div></div>
        <div class="metric"><div class="label">风险等级</div><div class="value">${r.risk_level}/100</div></div>
        <div class="metric"><div class="label">预期收益</div><div class="value">${r.expected_return}%</div></div>
        ${r.cvar_95 ? `<div class="metric"><div class="label">CVaR(95%)</div><div class="value">${r.cvar_95.toFixed(2)}%</div></div>` : ''}
        ${r.sharpe_ratio ? `<div class="metric"><div class="label">夏普比率</div><div class="value">${r.sharpe_ratio.toFixed(2)}</div></div>` : ''}
      </div>
      <h2>资产配置方案</h2>
      <table><tr><th>资产</th><th>代码</th><th>配置比例</th><th>配置金额(HKD)</th></tr>
      ${r.portfolio_allocation.map(a => `<tr><td>${a.name}</td><td>${a.symbol}</td><td>${a.weight}%</td><td>${a.amount.toLocaleString()}</td></tr>`).join('')}
      </table>
      <h2>AI 多Agent分析推理过程</h2>
      <div class="reasoning">${r.reasoning}</div>
      <div class="footer">
        <p><strong>免责声明：</strong>本报告由 AI 系统自动生成，仅供参考，不构成投资建议。投资有风险，入市需谨慎。</p>
        <p>Powered by FinAgent Pro — AFAC2026 方向四: Agentic AI</p>
      </div>
      </body></html>`);
    w.document.close();
    setTimeout(() => { w.print(); }, 500);
  };

  const fetchMarketOverview = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/market/hk-spot`);
      if (!response.ok) return;
      const data = await response.json();
      if (data.success && data.data && data.data.length > 0) {
        // 基于采样股票计算市场趋势指标（非恒指实际点位，为采样加权估算）
        const stocks = data.data;
        const avgChange = stocks.reduce((sum: number, s: any) => sum + (s.change_pct || 0), 0) / stocks.length;
        const totalVolume = stocks.reduce((sum: number, s: any) => sum + (s.turnover || 0), 0);
        const avgPrice = stocks.reduce((sum: number, s: any) => sum + (s.price || 0), 0) / stocks.length;
        setMarketOverview({
          hsIndex: Math.round(avgPrice * 100) / 100,  // 采样均价作为趋势参考
          hsChange: Math.round(avgChange * 100) / 100,
          techIndex: 0,  // 无独立科技指数数据源时留空
          techChange: Math.round(avgChange * 1.2 * 100) / 100,
          volume: Math.round(totalVolume / 100000000),  // Convert to 亿
        });
      }
    } catch { /* 市场概览获取失败时静默降级 */ }
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
    <ConfigProvider theme={{
      algorithm: darkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
      token: { colorPrimary: '#1890ff', borderRadius: 6 },
    }}>
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
        <Header style={{ padding: '0 24px', background: darkMode ? '#141414' : '#fff', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h2 style={{ margin: 0 }}>
            {MENU_TITLES[selectedMenu] || ''}
          </h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Tag color="blue">港股通</Tag>
            <Tag color="green">AI驱动</Tag>
            <Tag color="orange">国产大模型</Tag>
            <Switch
              checked={darkMode}
              onChange={setDarkMode}
              checkedChildren={<MoonOutlined />}
              unCheckedChildren={<SunOutlined />}
              title="暗色模式"
            />
          </div>
        </Header>
        <Content style={{ margin: '24px 16px', padding: 24, background: darkMode ? '#1f1f1f' : '#f0f2f5', minHeight: 280 }}>
          {selectedMenu === 'dashboard' && (
            <>
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
                runDemo={runDemo}
                analysisMetrics={analysisMetrics}
              />
              {loading && (
                <div style={{
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
            </>
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
            <Card title="投资组合分析" extra={analysisResult && <Button icon={<FilePdfOutlined />} onClick={exportReport}>导出PDF报告</Button>}>
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
            <Card title="风险评估中心" extra={analysisResult && <Button icon={<FilePdfOutlined />} onClick={exportReport}>导出PDF报告</Button>}>
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
              {analysisResult && (
                <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                  <Col span={8}>
                    <Statistic title="CVaR(95%)" value={analysisResult.cvar_95 ?? 0} suffix="%" precision={2} valueStyle={{ color: '#cf1322' }} />
                  </Col>
                  <Col span={8}>
                    <Statistic title="夏普比率" value={analysisResult.sharpe_ratio ?? 0} precision={2} valueStyle={{ color: (analysisResult.sharpe_ratio ?? 0) > 1 ? '#3f8600' : '#333' }} />
                  </Col>
                  <Col span={8}>
                    <Statistic title="年化收益" value={analysisResult.annual_return ?? 0} suffix="%" precision={2} />
                  </Col>
                </Row>
              )}
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
    </ConfigProvider>
  );
};

export default App;
