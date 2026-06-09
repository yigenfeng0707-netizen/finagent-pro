import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, AsyncIterator, Optional, Callable
from models.schemas import (
    AgentMessage, AgentRole, AgentStatus, TaskStep, AnalysisPlan,
    AgentContext, FinalReport
)
from agents import MarketAnalyst, RiskManager, PortfolioAdvisor, SentimentScanner
from knowledge.finance_kb import FinanceKnowledgeBase


class AgentOrchestrator:
    """Agent编排器 - 负责任务规划、链式执行、上下文传递"""

    def __init__(self):
        self.market_analyst = MarketAnalyst()
        self.risk_manager = RiskManager()
        self.portfolio_advisor = PortfolioAdvisor()
        self.sentiment_scanner = SentimentScanner()
        self.knowledge_base = FinanceKnowledgeBase()
        self._progress_callbacks: List[Callable] = []

    def on_progress(self, callback: Callable):
        self._progress_callbacks.append(callback)

    async def _notify(self, message: AgentMessage):
        for cb in self._progress_callbacks:
            if asyncio.iscoroutinefunction(cb):
                await cb(message)
            else:
                cb(message)

    def _build_plan(self, symbols: List[str], risk_preference: str) -> AnalysisPlan:
        steps = [
            TaskStep(step_id=1, agent_role=AgentRole.MARKET_ANALYST,
                     description=f"分析{symbols[0] if symbols else '港股'}市场行情",
                     depends_on=[], input_keys=[], output_key="market_analysis"),
            TaskStep(step_id=2, agent_role=AgentRole.SENTIMENT_SCANNER,
                     description=f"扫描{symbols[0] if symbols else '港股'}市场情绪",
                     depends_on=[1], input_keys=["market_analysis"],
                     output_key="sentiment_analysis"),
            TaskStep(step_id=3, agent_role=AgentRole.RISK_MANAGER,
                     description="评估投资组合风险",
                     depends_on=[1, 2], input_keys=["market_analysis", "sentiment_analysis"],
                     output_key="risk_analysis"),
            TaskStep(step_id=4, agent_role=AgentRole.PORTFOLIO_ADVISOR,
                     description="生成最终资产配置方案",
                     depends_on=[1, 2, 3],
                     input_keys=["market_analysis", "sentiment_analysis", "risk_analysis"],
                     output_key="final_advice"),
        ]
        return AnalysisPlan(
            plan_id=str(uuid.uuid4())[:8],
            steps=steps,
            total_steps=len(steps),
            created_at=datetime.now().isoformat()
        )

    async def run(self, symbols: List[str], investment_amount: float,
                  risk_preference: str = "moderate",
                  market: str = "hk") -> AsyncIterator[AgentMessage]:
        context = AgentContext(
            user_input=f"分析{'/'.join(symbols)}，{risk_preference}型，{investment_amount}HKD",
            symbols=symbols, risk_preference=risk_preference,
            investment_amount=investment_amount, market=market,
            plan=self._build_plan(symbols, risk_preference)
        )

        plan_msg = AgentMessage(
            agent="编排器", role=AgentRole.ORCHESTRATOR,
            content=f"规划完成: 共{context.plan.total_steps}个步骤 → 市场分析→情绪扫描→风险评估→组合建议",
            status=AgentStatus.COMPLETED,
            timestamp=datetime.now().strftime("%H:%M:%S"),
            data={"plan": [s.description for s in context.plan.steps]}
        )
        yield plan_msg
        await self._notify(plan_msg)

        symbol_list = [{"symbol": s, "market": market, "weight": 1.0 / len(symbols)} for s in symbols]

        # Step 1: 市场分析
        step1_msg = AgentMessage(
            agent="编排器", role=AgentRole.ORCHESTRATOR,
            content=f"步骤1/4: 启动市场分析师 → 分析{symbols[0] if symbols else '港股'}",
            status=AgentStatus.RUNNING,
            timestamp=datetime.now().strftime("%H:%M:%S")
        )
        yield step1_msg
        await self._notify(step1_msg)

        ma_result = await self.market_analyst.analyze(
            symbol=symbols[0] if symbols else "00700",
            market=market, context=context.results
        )
        context.results["market_analysis"] = ma_result
        yield ma_result
        await self._notify(ma_result)

        # Step 2: 情绪扫描
        step2_msg = AgentMessage(
            agent="编排器", role=AgentRole.ORCHESTRATOR,
            content=f"步骤2/4: 启动情绪扫描器 → 基于市场分析扫描情绪",
            status=AgentStatus.RUNNING,
            timestamp=datetime.now().strftime("%H:%M:%S")
        )
        yield step2_msg
        await self._notify(step2_msg)

        ss_result = await self.sentiment_scanner.scan(
            symbol=symbols[0] if symbols else "00700",
            market=market, context=context.results
        )
        context.results["sentiment_analysis"] = ss_result
        yield ss_result
        await self._notify(ss_result)

        # Step 3: 风险评估
        step3_msg = AgentMessage(
            agent="编排器", role=AgentRole.ORCHESTRATOR,
            content="步骤3/4: 启动风险经理 → 综合市场分析和情绪进行风险评估",
            status=AgentStatus.RUNNING,
            timestamp=datetime.now().strftime("%H:%M:%S")
        )
        yield step3_msg
        await self._notify(step3_msg)

        rm_result = await self.risk_manager.analyze(
            symbols=symbol_list, context=context.results,
            market_analysis=ma_result
        )
        context.results["risk_analysis"] = rm_result
        yield rm_result
        await self._notify(rm_result)

        # Step 4: 组合建议
        step4_msg = AgentMessage(
            agent="编排器", role=AgentRole.ORCHESTRATOR,
            content="步骤4/4: 启动组合顾问 → 综合所有分析生成最终方案",
            status=AgentStatus.RUNNING,
            timestamp=datetime.now().strftime("%H:%M:%S")
        )
        yield step4_msg
        await self._notify(step4_msg)

        pa_result = await self.portfolio_advisor.advise(
            risk_profile=risk_preference,
            investment_amount=investment_amount,
            symbols=symbols, context=context.results,
            market_analysis=ma_result,
            risk_analysis=rm_result,
            sentiment_analysis=ss_result
        )
        context.results["final_advice"] = pa_result
        yield pa_result
        await self._notify(pa_result)

        done_msg = AgentMessage(
            agent="编排器", role=AgentRole.ORCHESTRATOR,
            content="所有Agent分析完成，生成最终报告",
            status=AgentStatus.COMPLETED,
            timestamp=datetime.now().strftime("%H:%M:%S")
        )
        yield done_msg
        await self._notify(done_msg)

    def synthesize_report(self, context: AgentContext) -> FinalReport:
        ma = context.results.get("market_analysis")
        rm = context.results.get("risk_analysis")
        ss = context.results.get("sentiment_analysis")
        pa = context.results.get("final_advice")

        has_data = any([ma, rm, ss, pa])
        risk_level = 50
        if rm and rm.data:
            risk_level = rm.data.get("risk_level", 50)

        expected_return = 8.0
        portfolio_allocation = []
        if pa and pa.data:
            expected_return = pa.data.get("expected_return", 8.0)
            portfolio_allocation = pa.data.get("portfolio_allocation", [])

        reasoning_parts = []
        if ma:
            reasoning_parts.append(f"【市场分析】{ma.content[:150]}")
        if ss:
            reasoning_parts.append(f"【情绪分析】{ss.content[:100]}")
        if rm:
            reasoning_parts.append(f"【风险评估】风险等级{risk_level}/100")
        if pa:
            reasoning_parts.append(f"【配置建议】{pa.content[:150]}")

        recommendation = "hold"
        if has_data:
            recommendation = "buy" if risk_level < 60 else "hold"

        return FinalReport(
            recommendation=recommendation,
            confidence=0.78,
            risk_level=risk_level,
            expected_return=expected_return,
            reasoning="\n".join(reasoning_parts),
            portfolio_allocation=portfolio_allocation,
            agent_messages=[
                ma, ss, rm, pa
            ] if all([ma, ss, rm, pa]) else []
        )
