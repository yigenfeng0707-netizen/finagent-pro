from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    MARKET_ANALYST = "market_analyst"
    RISK_MANAGER = "risk_manager"
    PORTFOLIO_ADVISOR = "portfolio_advisor"
    SENTIMENT_SCANNER = "sentiment_scanner"
    ORCHESTRATOR = "orchestrator"


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentMessage(BaseModel):
    agent: str
    role: AgentRole
    content: str
    status: AgentStatus = AgentStatus.COMPLETED
    timestamp: str = ""
    confidence: float = 0.0
    data: Optional[Dict[str, Any]] = None
    thinking: Optional[str] = None

    class Config:
        use_enum_values = True


class TaskStep(BaseModel):
    step_id: int
    agent_role: AgentRole
    description: str
    depends_on: List[int] = []
    input_keys: List[str] = []
    output_key: str = ""


class AnalysisPlan(BaseModel):
    plan_id: str
    steps: List[TaskStep]
    total_steps: int
    created_at: str = ""


class AgentContext(BaseModel):
    user_input: str
    symbols: List[str] = []
    risk_preference: str = "moderate"
    investment_amount: float = 100000
    market: str = "hk"
    plan: Optional[AnalysisPlan] = None
    results: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    recommendation: str
    confidence: float
    risk_level: int
    expected_return: float
    reasoning: str
    portfolio_allocation: List[Dict[str, Any]]
    agent_messages: List[AgentMessage]


class OrchestratorRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1, max_length=10, description="股票代码列表")
    investment_amount: float = Field(default=100000, gt=0, description="投资金额")
    risk_preference: Literal["conservative", "moderate", "aggressive"] = "moderate"
    market: Literal["hk"] = "hk"
    session_id: Optional[str] = None


class OrchestratorResponse(BaseModel):
    status: str
    data: Optional[FinalReport] = None
    error: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class StockAnalysisRequest(BaseModel):
    symbol: str
    market: str = "hk"


class PortfolioRequest(BaseModel):
    risk_profile: str
    investment_amount: float
    investment_horizon: str = "medium"


class RiskAnalysisRequest(BaseModel):
    portfolio: List[Dict[str, Any]]


class WebSocketMessage(BaseModel):
    type: str
    payload: Dict[str, Any]
