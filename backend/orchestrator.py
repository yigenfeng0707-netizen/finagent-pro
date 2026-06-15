import asyncio
import uuid
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set

from agents import MarketAnalyst, PortfolioAdvisor, RiskManager, SentimentScanner
from knowledge.finance_kb import FinanceKnowledgeBase
from loguru import logger
from models.schemas import AgentContext, AgentMessage, AgentRole, AgentStatus, AnalysisPlan, FinalReport, TaskStep


class AgentOrchestrator:
    """Agent编排器 - 基于DAG的任务调度，支持并行执行、动态步骤、失败容错"""

    def __init__(self):
        self.market_analyst = MarketAnalyst()
        self.risk_manager = RiskManager()
        self.portfolio_advisor = PortfolioAdvisor()
        self.sentiment_scanner = SentimentScanner()
        self.knowledge_base = FinanceKnowledgeBase()
        self._progress_callbacks: Dict[str, Callable] = {}

        # Agent 执行器映射
        self._executors: Dict[AgentRole, Callable] = {
            AgentRole.MARKET_ANALYST: self._run_market_analyst,
            AgentRole.SENTIMENT_SCANNER: self._run_sentiment_scanner,
            AgentRole.RISK_MANAGER: self._run_risk_manager,
            AgentRole.PORTFOLIO_ADVISOR: self._run_portfolio_advisor,
        }

    def on_progress(self, session_id: str, callback: Callable):
        self._progress_callbacks[session_id] = callback

    def remove_progress(self, session_id: str):
        self._progress_callbacks.pop(session_id, None)

    async def _notify(self, session_id: str, message: AgentMessage):
        cb = self._progress_callbacks.get(session_id)
        if cb:
            if asyncio.iscoroutinefunction(cb):
                await cb(message)
            else:
                cb(message)

    def _build_plan(self, symbols: List[str], risk_preference: str) -> AnalysisPlan:
        """构建分析计划 — 市场分析和情绪扫描可并行，风险评估依赖前两者"""
        steps = [
            TaskStep(
                step_id=1,
                agent_role=AgentRole.MARKET_ANALYST,
                description=f"分析{symbols[0] if symbols else '港股'}市场行情",
                depends_on=[],
                input_keys=[],
                output_key="market_analysis",
            ),
            TaskStep(
                step_id=2,
                agent_role=AgentRole.SENTIMENT_SCANNER,
                description=f"扫描{symbols[0] if symbols else '港股'}市场情绪",
                depends_on=[],
                input_keys=[],
                output_key="sentiment_analysis",
            ),
            TaskStep(
                step_id=3,
                agent_role=AgentRole.RISK_MANAGER,
                description="评估投资组合风险",
                depends_on=[1, 2],
                input_keys=["market_analysis", "sentiment_analysis"],
                output_key="risk_analysis",
            ),
            TaskStep(
                step_id=4,
                agent_role=AgentRole.PORTFOLIO_ADVISOR,
                description="生成最终资产配置方案",
                depends_on=[1, 2, 3],
                input_keys=["market_analysis", "sentiment_analysis", "risk_analysis"],
                output_key="final_advice",
            ),
        ]
        return AnalysisPlan(
            plan_id=str(uuid.uuid4())[:8], steps=steps, total_steps=len(steps), created_at=datetime.now().isoformat()
        )

    def _get_ready_steps(self, plan: AnalysisPlan, completed: Set[int], running: Set[int]) -> List[TaskStep]:
        """获取当前可执行的步骤（依赖已满足且未在运行/已完成）"""
        ready = []
        for step in plan.steps:
            if step.step_id in completed or step.step_id in running:
                continue
            if all(dep in completed for dep in step.depends_on):
                ready.append(step)
        return ready

    async def _run_step(
        self,
        step: TaskStep,
        context: AgentContext,
        session_id: str,
        symbols: List[str],
        market: str,
        investment_amount: float,
        risk_preference: str,
        timeout: int = 90,
    ) -> AsyncIterator[AgentMessage]:
        """执行单个步骤，带超时和容错"""
        executor = self._executors.get(step.agent_role)
        if not executor:
            failed = self._make_failed_message(step.agent_role, f"未知Agent角色: {step.agent_role}")
            context.results[step.output_key] = failed
            yield failed
            return

        step_msg = AgentMessage(
            agent="编排器",
            role=AgentRole.ORCHESTRATOR,
            content=f"启动{step.agent_role.value} → {step.description}",
            status=AgentStatus.RUNNING,
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )
        yield step_msg

        try:
            result = await asyncio.wait_for(
                executor(
                    symbols=symbols, market=market, context=context.results,
                    investment_amount=investment_amount, risk_preference=risk_preference,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(f"步骤 {step.step_id} ({step.agent_role.value}) 执行超时")
            result = self._make_failed_message(step.agent_role, "执行超时")
        except Exception as e:
            logger.warning(f"步骤 {step.step_id} ({step.agent_role.value}) 执行失败: {e}")
            result = self._make_failed_message(step.agent_role, str(e))

        context.results[step.output_key] = result
        yield result

    def _make_failed_message(self, role: AgentRole, reason: str) -> AgentMessage:
        name_map = {
            AgentRole.MARKET_ANALYST: "市场分析师",
            AgentRole.SENTIMENT_SCANNER: "情绪扫描器",
            AgentRole.RISK_MANAGER: "风险经理",
            AgentRole.PORTFOLIO_ADVISOR: "组合顾问",
        }
        return AgentMessage(
            agent=name_map.get(role, "未知"),
            role=role,
            content=f"执行受限: {reason}",
            status=AgentStatus.FAILED,
            timestamp=datetime.now().strftime("%H:%M:%S"),
            data={"error": reason},
        )

    # ========== Agent 执行器 ==========

    async def _run_market_analyst(self, symbols: List[str], market: str, context: Dict, **kwargs) -> AgentMessage:
        return await self.market_analyst.analyze(symbol=symbols[0] if symbols else "00700", market=market, context=context)

    async def _run_sentiment_scanner(self, symbols: List[str], market: str, context: Dict, **kwargs) -> AgentMessage:
        return await self.sentiment_scanner.scan(symbol=symbols[0] if symbols else "00700", market=market, context=context)

    async def _run_risk_manager(self, symbols: List[str], market: str, context: Dict, **kwargs) -> AgentMessage:
        symbol_list = [{"symbol": s, "market": market, "weight": 1.0 / len(symbols)} for s in symbols]
        market_analysis = context.get("market_analysis")
        return await self.risk_manager.analyze(symbols=symbol_list, context=context, market_analysis=market_analysis)

    async def _run_portfolio_advisor(self, symbols: List[str], market: str, context: Dict, investment_amount: float = 100000, risk_preference: str = "moderate", **kwargs) -> AgentMessage:
        market_analysis = context.get("market_analysis")
        risk_analysis = context.get("risk_analysis")
        sentiment_analysis = context.get("sentiment_analysis")
        return await self.portfolio_advisor.advise(
            risk_profile=risk_preference, investment_amount=investment_amount,
            symbols=symbols, context=context,
            market_analysis=market_analysis, risk_analysis=risk_analysis, sentiment_analysis=sentiment_analysis,
        )

    # ========== 主执行流程 ==========

    async def run(
        self,
        symbols: List[str],
        investment_amount: float,
        risk_preference: str = "moderate",
        market: str = "hk",
        session_id: str = "",
    ) -> AsyncIterator[AgentMessage]:
        if not symbols:
            logger.warning("Orchestrator.run() 收到空 symbols 列表，使用默认标的")
            symbols = ["00700"]

        context = AgentContext(
            user_input=f"分析{'/'.join(symbols)}，{risk_preference}型，{investment_amount}HKD",
            symbols=symbols,
            risk_preference=risk_preference,
            investment_amount=investment_amount,
            market=market,
            plan=self._build_plan(symbols, risk_preference),
        )

        # 知识库增强
        kb_market = self.knowledge_base.get_context_for_query(f"港股 {symbols[0]} 市场分析 技术指标", n_results=2)
        kb_sentiment = self.knowledge_base.get_context_for_query("市场情绪 恐慌贪婪 投资心理", n_results=2)
        kb_risk = self.knowledge_base.get_context_for_query("风险管理 止损 VaR 波动率", n_results=2)
        kb_portfolio = self.knowledge_base.get_context_for_query(f"资产配置 {risk_preference}型投资者 组合优化", n_results=2)
        context.results["_kb_market"] = kb_market
        context.results["_kb_sentiment"] = kb_sentiment
        context.results["_kb_risk"] = kb_risk
        context.results["_kb_portfolio"] = kb_portfolio

        # 发送计划消息
        plan_msg = AgentMessage(
            agent="编排器",
            role=AgentRole.ORCHESTRATOR,
            content=f"规划完成: 共{context.plan.total_steps}个步骤 → 市场分析‖情绪扫描(并行)→风险评估→组合建议",
            status=AgentStatus.COMPLETED,
            timestamp=datetime.now().strftime("%H:%M:%S"),
            data={"plan": [s.description for s in context.plan.steps]},
        )
        yield plan_msg
        await self._notify(session_id, plan_msg)

        # DAG 执行
        completed: Set[int] = set()
        running: Set[int] = set()
        max_iterations = len(context.plan.steps) + 5  # 防止无限循环

        for _ in range(max_iterations):
            ready_steps = self._get_ready_steps(context.plan, completed, running)
            if not ready_steps and not running:
                break  # 所有步骤完成或无法继续

            # 并行启动所有就绪步骤
            tasks = []
            for step in ready_steps:
                running.add(step.step_id)
                tasks.append(self._execute_step_with_notifications(step, context, session_id, symbols, market, investment_amount, risk_preference))

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    step = ready_steps[i]
                    running.discard(step.step_id)
                    if isinstance(result, Exception):
                        logger.error(f"步骤 {step.step_id} 异常: {result}")
                        failed_msg = self._make_failed_message(step.agent_role, str(result))
                        context.results[step.output_key] = failed_msg
                    # 成功的结果已在 _execute_step_with_notifications 中写入 context
                    completed.add(step.step_id)

        # 发送完成消息
        done_msg = AgentMessage(
            agent="编排器",
            role=AgentRole.ORCHESTRATOR,
            content="所有Agent分析完成，生成最终报告",
            status=AgentStatus.COMPLETED,
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )
        yield done_msg
        await self._notify(session_id, done_msg)

    async def _execute_step_with_notifications(
        self, step: TaskStep, context: AgentContext, session_id: str,
        symbols: List[str], market: str, investment_amount: float, risk_preference: str,
    ) -> None:
        """执行步骤并通知进度，将所有 yield 的消息通过 _notify 发送"""
        async for msg in self._run_step(step, context, session_id, symbols, market, investment_amount, risk_preference):
            await self._notify(session_id, msg)

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
        confidence = 0.5
        if has_data:
            sentiment_score = 50
            if ss and ss.data:
                sentiment_score = ss.data.get("fear_greed_index", 50)

            market_bullish = False
            if ma and ma.content and any(w in ma.content for w in ["买入", "看多", "上涨", "突破"]):
                market_bullish = True

            if risk_level < 40 and sentiment_score > 55 and market_bullish:
                recommendation = "buy"
                confidence = min(0.95, 0.6 + (55 - risk_level) * 0.005 + (sentiment_score - 50) * 0.003)
            elif risk_level > 70 or sentiment_score < 30:
                recommendation = "sell"
                confidence = min(0.90, 0.5 + (risk_level - 70) * 0.005)
            else:
                recommendation = "hold"
                confidence = 0.55 + abs(sentiment_score - 50) * 0.003

        return FinalReport(
            recommendation=recommendation,
            confidence=round(confidence, 2),
            risk_level=risk_level,
            expected_return=expected_return,
            reasoning="\n".join(reasoning_parts),
            portfolio_allocation=portfolio_allocation,
            agent_messages=[msg for msg in [ma, ss, rm, pa] if msg is not None],
        )
