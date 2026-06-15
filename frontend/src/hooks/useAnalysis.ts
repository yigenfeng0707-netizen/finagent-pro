import { useCallback, useRef } from 'react';
import { message } from 'antd';
import { useAppStore } from '../stores/appStore';
import { useWebSocket, WSMessage } from './useWebSocket';
import { API_BASE } from '../constants';
import type { AgentFeedMessage } from '../components/LiveAgentFeed';
import type { ThinkingStep } from '../components/AgentThinkingPanel';
import type { WorkbenchStep, ToolCallEntry, HkSpotStock, AnalysisResult } from '../types';

function genId() {
  return 'sess_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}

export function useAnalysis() {
  const stepCounter = useRef(0);
  const analysisStartTime = useRef(0);
  const selectedStockRef = useRef(useAppStore.getState().selectedStock);
  const toolCallsRef = useRef<ToolCallEntry[]>([]);

  // 订阅 store 状态
  const {
    selectedStock, investmentAmount, riskPreference,
    sessionId, loading, wsConnected, authToken,
    setSessionId, setLoading, setAnalysisResult, setAnalysisMetrics,
    setAnalysisProgress, setFeedMessages, setThinkingSteps,
    setWorkbenchSteps, setToolCalls, setLiveContext, resetAnalysis,
  } = useAppStore();

  // 保持 ref 同步
  selectedStockRef.current = selectedStock;
  toolCallsRef.current = useAppStore.getState().toolCalls;

  const handleWSMessage = useCallback((msg: WSMessage) => {
    if (msg.type === 'agent_progress') {
      const p = msg.payload;
      type StepStatus = 'pending' | 'running' | 'completed' | 'failed';
      const role = String(p.role || '');
      const agent = String(p.agent || '');
      const content = String(p.content || '');
      const status = String(p.status || 'completed') as StepStatus;
      const timestamp = String(p.timestamp || '');
      const confidence = typeof p.confidence === 'number' ? p.confidence : undefined;
      const thinking = p.thinking ? String(p.thinking) : undefined;
      const data = p.data as Record<string, unknown> | undefined;

      // 更新进度
      const roleProgressMap: Record<string, { step: number; total: number; agentName: string }> = {
        MARKET_ANALYST: { step: 1, total: 4, agentName: '市场分析师' },
        SENTIMENT_SCANNER: { step: 2, total: 4, agentName: '情绪扫描器' },
        RISK_MANAGER: { step: 3, total: 4, agentName: '风险经理' },
        PORTFOLIO_ADVISOR: { step: 4, total: 4, agentName: '组合顾问' },
      };
      if (role && roleProgressMap[role]) {
        setAnalysisProgress(roleProgressMap[role]);
      }

      const feed: AgentFeedMessage = { agent, role, content, status, timestamp, confidence, thinking };
      setFeedMessages((prev: AgentFeedMessage[]) => [...prev, feed]);

      setThinkingSteps((prev: ThinkingStep[]) => {
        const existingIdx = prev.findIndex(s => s.role === role && s.status === 'running');
        if (existingIdx >= 0) {
          const updated = [...prev];
          updated[existingIdx] = { ...updated[existingIdx], status, content, thinking: thinking || undefined, confidence, data };
          return updated;
        }
        if (status === 'running' || !prev.find(s => s.role === role)) {
          stepCounter.current += 1;
          return [...prev, { stepId: stepCounter.current, agent, role, content, thinking, status, timestamp, confidence, data }];
        }
        return prev;
      });

      if (thinking) {
        setWorkbenchSteps((prev: WorkbenchStep[]) => {
          const exists = prev.find(s => s.role === role);
          if (exists) return prev.map(s => s.role === role ? { ...s, status } : s);
          return [...prev, {
            stepId: stepCounter.current, agent, role,
            description: `${agent} 正在执行...`,
            status: status === 'running' ? 'running' : status,
            dependsOn: [], inputKeys: [], outputKey: role + '_analysis',
          }];
        });
      }

      if (data) {
        setLiveContext((prev: Record<string, string>) => ({ ...prev, [role + '_analysis']: JSON.stringify(data).slice(0, 200) }));
      }

      // 提取工具调用
      if (data && role !== 'orchestrator') {
        const currentSymbol = selectedStockRef.current;
        const toolEntries: ToolCallEntry[] = [];
        if (data.current_price !== undefined) {
          toolEntries.push({ agent, tool: 'get_stock_price', args: `symbol=${currentSymbol}`, result: `价格: ${data.current_price} HKD`, timestamp: timestamp || new Date().toLocaleTimeString() });
        }
        if (data.rsi !== undefined) {
          toolEntries.push({ agent, tool: 'get_technical_indicators', args: `symbol=${currentSymbol}`, result: `RSI: ${data.rsi}, MA5: ${(data.ma5 as number) || 'N/A'}`, timestamp: timestamp || new Date().toLocaleTimeString() });
        }
        if (data.risk_data) {
          const riskData = data.risk_data as Record<string, unknown>;
          toolEntries.push({ agent, tool: 'get_portfolio_risk', args: `symbols=${currentSymbol}`, result: `波动率: ${riskData?.portfolio_volatility || 'N/A'}%`, timestamp: timestamp || new Date().toLocaleTimeString() });
        }
        if (toolEntries.length > 0) {
          setToolCalls((prev: ToolCallEntry[]) => [...prev, ...toolEntries]);
        }
      }
    } else if (msg.type === 'final_report') {
      const report = msg.payload as unknown as AnalysisResult;
      setAnalysisResult(report);
      setAnalysisProgress({ step: 5, total: 4, agentName: '' });
      setAnalysisMetrics({
        duration: (Date.now() - analysisStartTime.current) / 1000,
        toolCalls: useAppStore.getState().toolCalls.length,
        agents: 4,
      });
      setLoading(false);
      message.success('多Agent分析完成！');
      setTimeout(() => setSessionId(null), 2000);
    }
  }, [setAnalysisProgress, setFeedMessages, setThinkingSteps, setWorkbenchSteps, setLiveContext, setToolCalls, setAnalysisResult, setAnalysisMetrics, setLoading, setSessionId]);

  const wsHandler = useWebSocket(sessionId, {
    onMessage: handleWSMessage,
    onConnect: () => useAppStore.getState().setWsConnected(true),
    onDisconnect: () => useAppStore.getState().setWsConnected(false),
    enabled: !!sessionId && loading,
    token: authToken || undefined,
  });

  const runAnalysis = useCallback(async (stock?: string, amount?: number, risk?: string) => {
    setLoading(true);
    setAnalysisResult(null);
    setFeedMessages([]);
    setThinkingSteps([]);
    setWorkbenchSteps([]);
    setToolCalls([]);
    setLiveContext({});
    setAnalysisMetrics(null);
    setAnalysisProgress({ step: 0, total: 4, agentName: '' });
    analysisStartTime.current = Date.now();
    stepCounter.current = 0;

    const sid = genId();
    setSessionId(sid);

    try {
      // 等待 WebSocket 连接
      const wsReady = await new Promise<boolean>((resolve) => {
        if (useAppStore.getState().wsConnected) { resolve(true); return; }
        const checkInterval = setInterval(() => {
          if (useAppStore.getState().wsConnected) { clearInterval(checkInterval); resolve(true); }
        }, 100);
        setTimeout(() => { clearInterval(checkInterval); resolve(false); }, 3000);
      });

      stepCounter.current += 1;
      const planStep: ThinkingStep = {
        stepId: stepCounter.current, agent: '编排器', role: 'orchestrator',
        content: '规划完成: 共4个步骤 → 市场分析→情绪扫描→风险评估→组合建议',
        status: 'completed', timestamp: new Date().toLocaleTimeString(),
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
        setAnalysisResult(result.data);
        message.success('分析完成！');
        setLoading(false);
        setSessionId(null);
      }
    } catch {
      message.error('分析失败，请稍后重试');
      setLoading(false);
      setSessionId(null);
    }
  }, [selectedStock, investmentAmount, riskPreference, setLoading, setAnalysisResult, setFeedMessages, setThinkingSteps, setWorkbenchSteps, setToolCalls, setLiveContext, setAnalysisMetrics, setAnalysisProgress, setSessionId]);

  const runDemo = useCallback(() => {
    useAppStore.getState().setSelectedStock('00700');
    useAppStore.getState().setInvestmentAmount(100000);
    useAppStore.getState().setRiskPreference('moderate');
    runAnalysis('00700', 100000, 'moderate');
  }, [runAnalysis]);

  const fetchStockData = useCallback(async (symbol: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/market/stock/${symbol}?market=hk&days=180`);
      if (!response.ok) { message.error(`获取股票数据失败 (${response.status})`); return; }
      const data = await response.json();
      if (data.status === 'success') useAppStore.getState().setStockData(data.data);
    } catch { message.error('获取股票数据失败'); }
  }, []);

  const fetchMarketOverview = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/market/hk-spot`);
      if (!response.ok) return;
      const data = await response.json();
      if (data.success && data.data && data.data.length > 0) {
        const stocks = data.data;
        const avgChange = stocks.reduce((sum: number, s: HkSpotStock) => sum + (s.change_pct || 0), 0) / stocks.length;
        const totalVolume = stocks.reduce((sum: number, s: HkSpotStock) => sum + (s.turnover || 0), 0);
        const avgPrice = stocks.reduce((sum: number, s: HkSpotStock) => sum + (s.price || 0), 0) / stocks.length;
        useAppStore.getState().setMarketOverview({
          hsIndex: Math.round(avgPrice * 100) / 100,
          hsChange: Math.round(avgChange * 100) / 100,
          techIndex: 0,
          techChange: Math.round(avgChange * 1.2 * 100) / 100,
          volume: Math.round(totalVolume / 100000000),
        });
      }
    } catch { /* 静默降级 */ }
  }, []);

  const exportReport = useCallback(() => {
    const { analysisResult: r, selectedStock: s, investmentAmount: amt, riskPreference: rp } = useAppStore.getState();
    if (!r) { message.warning('请先执行分析后再导出报告'); return; }
    const w = window.open('', '_blank');
    if (!w) { message.error('无法打开导出窗口，请允许弹窗'); return; }
    w.document.write(`<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>FinAgent Pro 投资分析报告</title>
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
      <p>分析标的：${s} | 投资金额：HKD ${amt.toLocaleString()} | 风险偏好：${rp}</p>
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
  }, []);

  return {
    runAnalysis,
    runDemo,
    fetchStockData,
    fetchMarketOverview,
    exportReport,
    wsHandler,
  };
}
