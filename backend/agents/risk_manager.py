from typing import Any, Dict, List, Optional

from loguru import logger
from models.schemas import AgentMessage, AgentRole, AgentStatus
from tools.market_tools import MarketTools

from .base_agent import BaseAgent


class RiskManager(BaseAgent):
    def __init__(self, use_backup: bool = False):
        super().__init__(use_backup)
        self.agent = self.create_agent(
            role="首席风险官",
            goal="全面评估投资组合风险，提供风险预警和管理建议",
            backstory="你是一位拥有CFA和FRM双证的首席风险官，在顶级投行工作15年。"
            "你精通VaR模型、压力测试、情景分析等风险管理工具。"
            "你善于识别市场风险、信用风险、流动性风险等各类风险。",
        )
        self.register_tool("get_portfolio_risk", MarketTools.get_portfolio_risk)
        self.register_tool("calculate_var", MarketTools.calculate_var)
        self.register_tool("get_stock_price", MarketTools.get_stock_price)
        self.register_tool("stress_test", MarketTools.stress_test)

    async def analyze(
        self,
        symbols: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        market_analysis: Optional[AgentMessage] = None,
    ) -> AgentMessage:
        try:
            portfolio_risk = await self.call_tool("get_portfolio_risk", symbols=symbols)
            if "error" in portfolio_risk:
                return self.make_message(
                    agent_name="风险经理",
                    role=AgentRole.RISK_MANAGER,
                    content=f"风险评估失败: {portfolio_risk['error']}",
                    status=AgentStatus.FAILED,
                    data={"error": portfolio_risk["error"]},
                )

            risk_data = portfolio_risk
            risk_level_num = (
                25 if risk_data["risk_level"] == "低风险" else 55 if risk_data["risk_level"] == "中风险" else 80
            )

            market_context = ""
            if market_analysis and market_analysis.data:
                md = market_analysis.data
                market_context = (
                    f"市场分析补充:\n"
                    f"  - 目标股票当前价格: {md.get('current_price')} HKD\n"
                    f"  - 波动率: {md.get('volatility')}%\n"
                    f"  - RSI: {md.get('rsi')}\n"
                    f"  - 布林带位置: 上轨{md.get('bb_upper')}/下轨{md.get('bb_lower')}\n"
                )

            thinking = (
                f"正在评估组合风险...\n"
                f"组合波动率: {risk_data['portfolio_volatility']}%\n"
                f"VaR(95%): {risk_data['portfolio_var_95']}%\n"
                f"风险等级: {risk_data['risk_level']}\n"
                f"正在结合市场数据生成风控建议..."
            )

            stock_details = ""
            for s in risk_data.get("stock_risks", []):
                stock_details += (
                    f"  - {s['symbol']}: 权重{s['weight']*100:.0f}%, "
                    f"波动率{s['volatility']}%, VaR {s['var_95']}%, "
                    f"最大回撤{s['max_drawdown']}%\n"
                )

            prompt = (
                f"你是一位资深首席风险官。请基于以下数据评估投资组合风险。\n\n"
                f"组合风险指标:\n"
                f"  - 组合波动率: {risk_data['portfolio_volatility']}%\n"
                f"  - VaR(95%): {risk_data['portfolio_var_95']}%\n"
                f"  - 风险等级: {risk_data['risk_level']}\n\n"
                f"个股风险详情:\n{stock_details}\n"
                f"{market_context}\n"
                f"请提供:\n"
                f"1. 组合风险综合评估\n"
                f"2. 个股风险贡献度分析\n"
                f"3. 风险预警信号\n"
                f"4. 风险管理建议（如何降低风险）\n"
                f"5. 适合的投资者类型\n"
                f"请用中文回答，保持专业且简洁。"
            )

            llm_output = await self.run_llm(prompt)

            return self.make_message(
                agent_name="风险经理",
                role=AgentRole.RISK_MANAGER,
                content=llm_output,
                confidence=0.75,
                data={"risk_level": risk_level_num, "risk_data": risk_data},
                thinking=thinking,
            )

        except Exception as e:
            logger.exception("风险经理执行失败")
            return self.make_message(
                agent_name="风险经理",
                role=AgentRole.RISK_MANAGER,
                content=f"风险经理遇到异常: {type(e).__name__}: {str(e)}",
                status=AgentStatus.FAILED,
                data={"error": str(e)},
            )
