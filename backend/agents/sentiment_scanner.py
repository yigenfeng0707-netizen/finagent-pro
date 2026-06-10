from .base_agent import BaseAgent
from models.schemas import AgentRole, AgentStatus, AgentMessage
from tools.market_tools import MarketTools
from typing import Dict, Any, Optional
from loguru import logger


class SentimentScanner(BaseAgent):
    def __init__(self, use_backup: bool = False):
        super().__init__(use_backup)
        self.agent = self.create_agent(
            role="市场情绪分析师",
            goal="实时监控和分析市场情绪，识别恐慌和贪婪信号",
            backstory="你是一位经验丰富的市场情绪分析师，擅长从市场数据中捕捉情绪变化。"
                       "你能够识别市场的恐慌和贪婪，判断情绪对股价的影响。"
                       "你的分析敏锐、及时，能够帮助投资者把握市场情绪转折点。"
        )
        self.register_tool("get_stock_price", MarketTools.get_stock_price)
        self.register_tool("get_technical_indicators", MarketTools.get_technical_indicators)

    async def scan(self, symbol: str, market: str = "hk",
                   context: Optional[Dict[str, Any]] = None) -> AgentMessage:
        try:
            price_data = await self.call_tool("get_stock_price", symbol=symbol, market=market)
            indicators = await self.call_tool("get_technical_indicators", symbol=symbol, market=market)

            rsi = indicators.get("rsi")
            volatility = indicators.get("volatility", 0)
            change_pct = indicators.get("change_pct", 0)

            if rsi is not None:
                if rsi > 70:
                    sentiment_label = "偏乐观（超买区）"
                    fear_greed = 75
                elif rsi > 55:
                    sentiment_label = "乐观"
                    fear_greed = 65
                elif rsi > 45:
                    sentiment_label = "中性"
                    fear_greed = 50
                elif rsi > 30:
                    sentiment_label = "偏悲观"
                    fear_greed = 35
                else:
                    sentiment_label = "悲观（超卖区）"
                    fear_greed = 20
            else:
                sentiment_label = "未知"
                fear_greed = 50

            thinking = (
                f"正在扫描市场情绪...\n"
                f"目标: {symbol}\n"
                f"RSI: {rsi} | 情绪: {sentiment_label}\n"
                f"涨跌幅: {change_pct}% | 波动率: {volatility}%\n"
                f"恐惧贪婪指数: {fear_greed}/100\n"
                "正在综合市场数据生成情绪分析..."
            )

            prompt = (
                f"你是一位市场情绪分析师。请基于以下数据分析市场情绪。\n\n"
                f"股票代码: {symbol}\n"
                f"当前价格: {price_data.get('price', 'N/A')} HKD\n"
                f"涨跌幅: {change_pct}%\n"
                f"技术指标:\n"
                f"  - RSI(14): {rsi}\n"
                f"  - 波动率: {volatility}%\n\n"
                f"情绪信号:\n"
                f"  - 恐惧贪婪指数: {fear_greed}/100\n"
                f"  - 情绪标签: {sentiment_label}\n\n"
                f"请提供:\n"
                f"1. 市场情绪综合评估\n"
                f"2. 情绪对股价的潜在影响\n"
                f"3. 可能的情绪转折点\n"
                f"4. 基于情绪的投资建议\n"
                f"请用中文回答，保持专业且简洁。"
            )

            llm_output = await self.run_llm(prompt)

            return self.make_message(
                agent_name="情绪扫描器",
                role=AgentRole.SENTIMENT_SCANNER,
                content=llm_output,
                confidence=0.7,
                data={
                    "fear_greed_index": fear_greed,
                    "fear_greed_label": sentiment_label,
                    "rsi": rsi,
                    "volatility": volatility,
                    "change_pct": change_pct
                },
                thinking=thinking
            )

        except Exception as e:
            logger.exception("情绪扫描器执行失败")
            return self.make_message(
                agent_name="情绪扫描器",
                role=AgentRole.SENTIMENT_SCANNER,
                content=f"情绪扫描器遇到异常: {type(e).__name__}: {str(e)}",
                status=AgentStatus.FAILED,
                data={"error": str(e)}
            )
