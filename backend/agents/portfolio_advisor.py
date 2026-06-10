from .base_agent import BaseAgent
from models.schemas import AgentRole, AgentStatus, AgentMessage
from typing import Dict, Any, Optional, List
from loguru import logger


class PortfolioAdvisor(BaseAgent):
    def __init__(self, use_backup: bool = False):
        super().__init__(use_backup)
        self.agent = self.create_agent(
            role="资深资产配置专家",
            goal="根据投资者风险偏好和目标，提供最优资产配置方案",
            backstory="你是一位拥有CFA证书的资深资产配置专家，曾在全球顶级资管公司工作。"
                       "你精通现代投资组合理论、马科维茨模型、黑-李特曼模型等资产配置方法。"
                       "你善于根据投资者的风险承受能力、投资期限、收益目标，定制个性化投资方案。"
        )

    async def advise(self, risk_profile: str, investment_amount: float,
                     investment_horizon: str = "medium",
                     symbols: Optional[List[str]] = None,
                     context: Optional[Dict[str, Any]] = None,
                     market_analysis: Optional[AgentMessage] = None,
                     risk_analysis: Optional[AgentMessage] = None,
                     sentiment_analysis: Optional[AgentMessage] = None) -> AgentMessage:
        try:
            profile_map = {"conservative": "保守型", "moderate": "稳健型", "aggressive": "进取型"}
            horizon_map = {"short": "短期(1年内)", "medium": "中期(1-3年)", "long": "长期(3年以上)"}
            profile_cn = profile_map.get(risk_profile, "稳健型")
            horizon_cn = horizon_map.get(investment_horizon, "中期(1-3年)")

            allocation_templates = {
                "conservative": {"stocks": 30, "bonds": 50, "cash": 15, "gold": 5, "exp_return": 5.0, "vol": 8.0},
                "moderate": {"stocks": 50, "bonds": 35, "cash": 10, "gold": 5, "exp_return": 8.0, "vol": 15.0},
                "aggressive": {"stocks": 70, "bonds": 20, "cash": 5, "gold": 5, "exp_return": 12.0, "vol": 25.0}
            }
            tmpl = allocation_templates.get(risk_profile, allocation_templates["moderate"])
            if investment_horizon == "long":
                tmpl["stocks"] += 5; tmpl["bonds"] -= 5; tmpl["exp_return"] += 1.0
            elif investment_horizon == "short":
                tmpl["stocks"] -= 5; tmpl["cash"] += 5; tmpl["exp_return"] -= 1.0

            portfolio_allocation = [
                {"symbol": "STOCKS", "name": "股票", "weight": tmpl["stocks"],
                 "amount": round(investment_amount * tmpl["stocks"] / 100, 2)},
                {"symbol": "BONDS", "name": "债券", "weight": tmpl["bonds"],
                 "amount": round(investment_amount * tmpl["bonds"] / 100, 2)},
                {"symbol": "CASH", "name": "现金", "weight": tmpl["cash"],
                 "amount": round(investment_amount * tmpl["cash"] / 100, 2)},
                {"symbol": "GOLD", "name": "黄金", "weight": tmpl["gold"],
                 "amount": round(investment_amount * tmpl["gold"] / 100, 2)},
            ]

            symbol_context = ""
            if symbols:
                symbol_context = f"关注股票: {', '.join(symbols)}\n"

            analysis_context = ""
            if market_analysis:
                analysis_context += f"市场分析摘要: {market_analysis.content[:200]}...\n"
            if risk_analysis:
                risk_level = risk_analysis.data.get("risk_level", 50) if risk_analysis.data else 50
                analysis_context += f"风险评估: 风险等级{risk_level}/100\n"
            if sentiment_analysis:
                analysis_context += f"情绪分析摘要: {sentiment_analysis.content[:100]}...\n"

            thinking = (
                f"正在生成资产配置方案...\n"
                f"投资者画像: {profile_cn} | {horizon_cn}\n"
                f"投资金额: {investment_amount} HKD\n"
                f"建议配置: 股票{tmpl['stocks']}% / 债券{tmpl['bonds']}% "
                f"/ 现金{tmpl['cash']}% / 黄金{tmpl['gold']}%\n"
                f"预期年化收益: {tmpl['exp_return']}% | 预期波动率: {tmpl['vol']}%\n"
                "正在综合考虑市场分析和风险评估优化配置..."
            )

            prompt = (
                f"你是一位资深资产配置专家。请基于以下信息提供资产配置建议。\n\n"
                f"投资者画像:\n"
                f"  - 风险偏好: {profile_cn}\n"
                f"  - 投资金额: {investment_amount} HKD\n"
                f"  - 投资期限: {horizon_cn}\n"
                f"{symbol_context}\n"
                f"{analysis_context}\n"
                f"基准配置方案:\n"
                f"  - 股票: {tmpl['stocks']}%\n"
                f"  - 债券: {tmpl['bonds']}%\n"
                f"  - 现金: {tmpl['cash']}%\n"
                f"  - 黄金: {tmpl['gold']}%\n"
                f"  - 预期年化收益: {tmpl['exp_return']}%\n"
                f"  - 预期波动率: {tmpl['vol']}%\n\n"
                f"请提供:\n"
                f"1. 配置逻辑说明（为什么选择这个比例）\n"
                f"2. 具体投资标的建议（港股为主）\n"
                f"3. 再平衡策略\n"
                f"4. 预期收益测算（1年/3年/5年）\n"
                f"请用中文回答，保持专业且简洁。"
            )

            llm_output = await self.run_llm(prompt)

            return self.make_message(
                agent_name="组合顾问",
                role=AgentRole.PORTFOLIO_ADVISOR,
                content=llm_output,
                confidence=0.8,
                data={
                    "portfolio_allocation": portfolio_allocation,
                    "expected_return": tmpl["exp_return"],
                    "expected_volatility": tmpl["vol"],
                    "risk_profile": risk_profile,
                    "investment_amount": investment_amount
                },
                thinking=thinking
            )

        except Exception as e:
            logger.exception("组合顾问执行失败")
            return self.make_message(
                agent_name="组合顾问",
                role=AgentRole.PORTFOLIO_ADVISOR,
                content=f"组合顾问遇到异常: {type(e).__name__}: {str(e)}",
                status=AgentStatus.FAILED,
                data={"error": str(e)}
            )
