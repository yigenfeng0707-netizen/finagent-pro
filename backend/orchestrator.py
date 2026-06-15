import asyncio
import json
import re
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
        """综合4个Agent输出，生成最终投资建议报告（规则引擎快速综合）"""
        ma = context.results.get("market_analysis")
        rm = context.results.get("risk_analysis")
        ss = context.results.get("sentiment_analysis")
        pa = context.results.get("final_advice")

        has_data = any([ma, rm, ss, pa])

        # ---- 风险指标提取 ----
        risk_level = 50
        cvar_95 = None
        sharpe_ratio = None
        annual_return = None
        annual_volatility = None
        if rm and rm.data:
            risk_level = rm.data.get("risk_level", rm.data.get("risk_level_num", 50))
            cvar_95 = rm.data.get("cvar_95")
            sharpe_ratio = rm.data.get("sharpe_ratio")
            annual_return = rm.data.get("annual_return")
            annual_volatility = rm.data.get("annual_volatility")

        # ---- 组合指标提取 ----
        expected_return = 8.0
        portfolio_allocation = []
        if pa and pa.data:
            expected_return = pa.data.get("expected_return", 8.0)
            portfolio_allocation = pa.data.get("portfolio_allocation", [])
            # 马科维茨优化结果优先
            if "optimal_portfolio" in pa.data:
                opt = pa.data["optimal_portfolio"]
                expected_return = opt.get("expected_return", expected_return)
                sharpe_ratio = opt.get("sharpe_ratio", sharpe_ratio)

        # ---- 多维度综合推理（替代简单关键词匹配） ----
        reasoning_parts = []
        if ma:
            reasoning_parts.append(f"【市场分析】{ma.content[:200]}")
        if ss:
            reasoning_parts.append(f"【情绪分析】{ss.content[:150]}")
        if rm:
            reasoning_parts.append(f"【风险评估】风险等级{risk_level}/100")
            if cvar_95 is not None:
                reasoning_parts.append(f"  CVaR(95%)={cvar_95}%")
            if sharpe_ratio is not None:
                reasoning_parts.append(f"  夏普比率={sharpe_ratio}")
        if pa:
            reasoning_parts.append(f"【配置建议】{pa.content[:200]}")

        recommendation = "hold"
        confidence = 0.5

        if has_data:
            # 多因子评分模型
            risk_score = 0.0   # 风险因子 (-1 到 +1)
            momentum_score = 0.0  # 动量因子 (-1 到 +1)
            sentiment_score_val = 0.0  # 情绪因子 (-1 到 +1)

            # 1. 风险因子：风险等级越低越利好
            risk_score = max(-1, min(1, (50 - risk_level) / 50))

            # 2. 情绪因子：恐惧贪婪指数
            fg_index = 50
            if ss and ss.data:
                fg_index = ss.data.get("fear_greed_index", 50)
            sentiment_score_val = max(-1, min(1, (fg_index - 50) / 50))

            # 3. 动量因子：技术面信号
            if ma and ma.content:
                bullish_words = ["买入", "看多", "上涨", "突破", "金叉", "超卖反弹", "支撑"]
                bearish_words = ["卖出", "看空", "下跌", "破位", "死叉", "超买", "阻力"]
                bull_count = sum(1 for w in bullish_words if w in ma.content)
                bear_count = sum(1 for w in bearish_words if w in ma.content)
                if bull_count + bear_count > 0:
                    momentum_score = (bull_count - bear_count) / (bull_count + bear_count)

            # 4. 夏普比率因子（如有）
            sharpe_factor = 0.0
            if sharpe_ratio is not None:
                sharpe_factor = max(-1, min(1, (sharpe_ratio - 1.0) / 2.0))

            # 综合评分（加权）
            composite = (risk_score * 0.30 + momentum_score * 0.25 +
                         sentiment_score_val * 0.25 + sharpe_factor * 0.20)

            if composite > 0.2:
                recommendation = "buy"
                confidence = min(0.95, 0.55 + composite * 0.40)
            elif composite < -0.2:
                recommendation = "sell"
                confidence = min(0.90, 0.55 + abs(composite) * 0.35)
            else:
                recommendation = "hold"
                confidence = 0.50 + abs(composite) * 0.20

        return FinalReport(
            recommendation=recommendation,
            confidence=round(confidence, 2),
            risk_level=risk_level,
            expected_return=expected_return,
            reasoning="\n".join(reasoning_parts),
            portfolio_allocation=portfolio_allocation,
            agent_messages=[msg for msg in [ma, ss, rm, pa] if msg is not None],
            cvar_95=cvar_95,
            sharpe_ratio=sharpe_ratio,
            annual_return=annual_return,
            annual_volatility=annual_volatility,
        )

    async def synthesize_report_with_llm(self, context: AgentContext) -> FinalReport:
        """LLM增强版综合报告 — 用大模型综合4个Agent输出，生成更智能的投资建议"""
        ma = context.results.get("market_analysis")
        rm = context.results.get("risk_analysis")
        ss = context.results.get("sentiment_analysis")
        pa = context.results.get("final_advice")

        # 先用规则引擎生成基础报告
        base_report = self.synthesize_report(context)

        # 如果没有LLM可用，直接返回规则引擎结果
        if not hasattr(self, 'market_analyst') or not self.market_analyst:
            return base_report

        # 构建LLM综合推理Prompt
        agent_summaries = []
        if ma:
            agent_summaries.append(f"【市场分析师报告】\n{ma.content[:500]}")
        if ss:
            agent_summaries.append(f"【情绪扫描器报告】\n{ss.content[:400]}")
        if rm:
            agent_summaries.append(f"【风险经理报告】\n{rm.content[:400]}")
            if rm.data:
                agent_summaries.append(f"  风险数据: {json.dumps({k: v for k, v in rm.data.items() if k in ['risk_level', 'risk_level_num', 'cvar_95', 'sharpe_ratio', 'annual_return', 'annual_volatility']}, ensure_ascii=False)}")
        if pa:
            agent_summaries.append(f"【组合顾问报告】\n{pa.content[:500]}")

        if not agent_summaries:
            return base_report

        prompt = f"""你是一位资深投资顾问，请综合以下4位AI分析师的报告，生成最终投资建议。

{chr(10).join(agent_summaries)}

请以JSON格式返回综合分析结果（不要包含其他文字）:
{{
  "recommendation": "buy|hold|sell",
  "confidence": 0.0-1.0,
  "reasoning": "综合推理过程，需引用各分析师的关键发现",
  "risk_summary": "风险概述（1-2句）",
  "action_suggestion": "具体操作建议"
}}"""

        try:
            import json
            response = await asyncio.wait_for(
                self.market_analyst.run_llm(prompt), timeout=30
            )
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                base_report.recommendation = result.get("recommendation", base_report.recommendation)
                base_report.confidence = min(0.95, max(0.3, float(result.get("confidence", base_report.confidence))))
                llm_reasoning = result.get("reasoning", "")
                if llm_reasoning:
                    base_report.reasoning = f"{base_report.reasoning}\n\n【AI综合推理】{llm_reasoning}"
                action = result.get("action_suggestion", "")
                if action:
                    base_report.reasoning += f"\n【操作建议】{action}"
        except Exception as e:
            logger.warning(f"LLM综合推理失败，使用规则引擎结果: {e}")

        return base_report
