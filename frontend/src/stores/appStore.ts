import { create } from 'zustand';
import type { StockData, AnalysisResult, WorkbenchStep, ToolCallEntry } from '../types';
import type { AgentFeedMessage } from '../components/LiveAgentFeed';
import type { ThinkingStep } from '../components/AgentThinkingPanel';

interface MarketOverview {
  hsIndex: number;
  hsChange: number;
  techIndex: number;
  techChange: number;
  volume: number;
}

interface AnalysisProgress {
  step: number;
  total: number;
  agentName: string;
}

interface AnalysisMetrics {
  duration: number;
  toolCalls: number;
  agents: number;
}

interface AppState {
  // 布局
  collapsed: boolean;
  darkMode: boolean;
  setCollapsed: (c: boolean) => void;
  setDarkMode: (d: boolean) => void;

  // 股票选择
  selectedStock: string;
  setSelectedStock: (s: string) => void;
  investmentAmount: number;
  setInvestmentAmount: (n: number) => void;
  riskPreference: string;
  setRiskPreference: (s: string) => void;

  // 市场数据
  stockData: StockData | null;
  setStockData: (d: StockData | null) => void;
  marketOverview: MarketOverview;
  setMarketOverview: (m: MarketOverview) => void;

  // 分析
  loading: boolean;
  setLoading: (l: boolean) => void;
  analysisResult: AnalysisResult | null;
  setAnalysisResult: (r: AnalysisResult | null) => void;
  analysisMetrics: AnalysisMetrics | null;
  setAnalysisMetrics: (m: AnalysisMetrics | null) => void;
  analysisProgress: AnalysisProgress;
  setAnalysisProgress: (p: AnalysisProgress) => void;

  // WebSocket
  sessionId: string | null;
  setSessionId: (s: string | null) => void;
  wsConnected: boolean;
  setWsConnected: (c: boolean) => void;

  // Agent 消息
  feedMessages: AgentFeedMessage[];
  setFeedMessages: (msgs: AgentFeedMessage[] | ((prev: AgentFeedMessage[]) => AgentFeedMessage[])) => void;
  thinkingSteps: ThinkingStep[];
  setThinkingSteps: (steps: ThinkingStep[] | ((prev: ThinkingStep[]) => ThinkingStep[])) => void;
  workbenchSteps: WorkbenchStep[];
  setWorkbenchSteps: (steps: WorkbenchStep[] | ((prev: WorkbenchStep[]) => WorkbenchStep[])) => void;
  toolCalls: ToolCallEntry[];
  setToolCalls: (calls: ToolCallEntry[] | ((prev: ToolCallEntry[]) => ToolCallEntry[])) => void;
  liveContext: Record<string, string>;
  setLiveContext: (ctx: Record<string, string> | ((prev: Record<string, string>) => Record<string, string>)) => void;

  // 认证
  authToken: string | null;
  setAuthToken: (t: string | null) => void;

  // 重置分析状态
  resetAnalysis: () => void;
}

const defaultProgress: AnalysisProgress = { step: 0, total: 4, agentName: '' };
const defaultMarketOverview: MarketOverview = { hsIndex: 0, hsChange: 0, techIndex: 0, techChange: 0, volume: 0 };

export const useAppStore = create<AppState>((set) => ({
  // 布局
  collapsed: false,
  darkMode: false,
  setCollapsed: (c) => set({ collapsed: c }),
  setDarkMode: (d) => set({ darkMode: d }),

  // 股票选择
  selectedStock: '00700',
  setSelectedStock: (s) => set({ selectedStock: s }),
  investmentAmount: 100000,
  setInvestmentAmount: (n) => set({ investmentAmount: n }),
  riskPreference: 'moderate',
  setRiskPreference: (s) => set({ riskPreference: s }),

  // 市场数据
  stockData: null,
  setStockData: (d) => set({ stockData: d }),
  marketOverview: defaultMarketOverview,
  setMarketOverview: (m) => set({ marketOverview: m }),

  // 分析
  loading: false,
  setLoading: (l) => set({ loading: l }),
  analysisResult: null,
  setAnalysisResult: (r) => set({ analysisResult: r }),
  analysisMetrics: null,
  setAnalysisMetrics: (m) => set({ analysisMetrics: m }),
  analysisProgress: defaultProgress,
  setAnalysisProgress: (p) => set({ analysisProgress: p }),

  // WebSocket
  sessionId: null,
  setSessionId: (s) => set({ sessionId: s }),
  wsConnected: false,
  setWsConnected: (c) => set({ wsConnected: c }),

  // Agent 消息
  feedMessages: [],
  setFeedMessages: (msgs) => set((state) => ({
    feedMessages: typeof msgs === 'function' ? msgs(state.feedMessages) : msgs,
  })),
  thinkingSteps: [],
  setThinkingSteps: (steps) => set((state) => ({
    thinkingSteps: typeof steps === 'function' ? steps(state.thinkingSteps) : steps,
  })),
  workbenchSteps: [],
  setWorkbenchSteps: (steps) => set((state) => ({
    workbenchSteps: typeof steps === 'function' ? steps(state.workbenchSteps) : steps,
  })),
  toolCalls: [],
  setToolCalls: (calls) => set((state) => ({
    toolCalls: typeof calls === 'function' ? calls(state.toolCalls) : calls,
  })),
  liveContext: {},
  setLiveContext: (ctx) => set((state) => ({
    liveContext: typeof ctx === 'function' ? ctx(state.liveContext) : ctx,
  })),

  // 认证
  authToken: null,
  setAuthToken: (t) => set({ authToken: t }),

  // 重置分析状态
  resetAnalysis: () => set({
    loading: false,
    analysisResult: null,
    analysisMetrics: null,
    analysisProgress: defaultProgress,
    feedMessages: [],
    thinkingSteps: [],
    workbenchSteps: [],
    toolCalls: [],
    liveContext: {},
    sessionId: null,
  }),
}));
