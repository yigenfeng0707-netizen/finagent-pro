/**
 * FinAgent Pro — 共享类型定义
 */

export interface StockData {
  dates: string[]; prices: number[]; volumes: number[];
  ma5?: number[]; ma20?: number[]; ma60?: number[];
  indicators?: Record<string, number | null>;
}

export interface AgentMessage {
  agent: string; role: string; content: string; timestamp: string;
  status?: string; confidence?: number; thinking?: string; data?: Record<string, unknown>;
}

export interface AnalysisResult {
  recommendation: string; confidence: number; risk_level: number;
  expected_return: number; reasoning: string;
  portfolio_allocation: Array<{symbol: string; name: string; weight: number; amount: number}>;
  agent_messages: AgentMessage[];
  cvar_95?: number; sharpe_ratio?: number; annual_return?: number; annual_volatility?: number;
}

export interface WorkbenchStep {
  stepId: number; agent: string; role: string; description: string;
  status: string; dependsOn: string[]; inputKeys: string[]; outputKey: string;
}

export interface ToolCallEntry {
  agent: string; tool: string; args: string; result: string; timestamp: string;
}

export interface HkSpotStock {
  price: number; change_pct: number; turnover: number;
  [key: string]: unknown;
}
