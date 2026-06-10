from .base_agent import BaseAgent
from models.schemas import AgentRole, AgentStatus, AgentMessage
from tools.market_tools import MarketTools
from typing import Dict, Any, Optional
from loguru import logger


class MarketAnalyst(BaseAgent):
    def __init__(self, use_backup: bool = False):
        super().__init__(use_backup)
        self.agent = self.create_agent(
            role="资深市场分析师",
            goal="深入分析港股市场行情，识别趋势和投资机会",
            backstory="你是一位拥有20年经验的资深市场分析师，精通技术分析和基本面分析。"
                       "你擅长分析股票走势、识别市场趋势、发现投资机会。"
                       "你的分析严谨、数据驱动，能够为投资决策提供有力支持。"
        )
        self.register_tool("get_stock_price", MarketTools.get_stock_price)
        self.register_tool("get_technical_indicators", MarketTools.get_technical_indicators)

    async def analyze(self, symbol: str, market: str = "hk",
                      context: Optional[Dict[str, Any]] = None) -> AgentMessage:
        try:
            indicators = await self.call_tool("get_technical_indicators", symbol=symbol, market=market)
            if "error" in indicators:
                return self.make_message(
                    agent_name="市场分析师",
                    role=AgentRole.MARKET_ANALYST,
                    content=f"分析失败: {indicators['error']}",
                    status=AgentStatus.FAILED,
                    data={"symbol": symbol, "error": indicators["error"]}
                )

            thinking = (
                f"正在分析 {symbol}...\n"
                f"当前价格: {indicators['current_price']} HKD\n"
                f"涨跌幅: {indicators['change_pct']}%\n"
                f"5日均线: {indicators['ma5']} | 20日均线: {indicators['ma20']}\n"
                f"RSI: {indicators['rsi']} | 波动率: {indicators['volatility']}%\n"
                f"布林带上轨: {indicators['bb_upper']} | 下轨: {indicators['bb_lower']}\n"
                "正在结合技术指标生成综合判断..."
            )

            prompt = (
                f"你是一位资深港股市场分析师。请分析以下股票数据并给出专业判断。\n\n"
                f"股票代码: {symbol}\n"
                f"当前价格: {indicators['current_price']} HKD\n"
                f"今日涨跌幅: {indicators['change_pct']}%\n"
                f"成交量: {indicators['volume']}\n"
                f"技术指标:\n"
                f"  - MA5: {indicators['ma5']}\n"
                f"  - MA20: {indicators['ma20']}\n"
                f"  - MA60: {indicators['ma60']}\n"
                f"  - MACD DIF: {indicators['macd_dif']}\n"
                f"  - RSI(14): {indicators['rsi']}\n"
                f"  - 波动率: {indicators['volatility']}%\n"
                f"  - 布林带上轨/下轨: {indicators['bb_upper']}/{indicators['bb_lower']}\n"
                f"  - 52周最高/最低: {indicators['high_52w']}/{indicators['low_52w']}\n\n"
                f"请提供:\n"
                f"1. 技术面分析（均线排列、趋势判断、支撑阻力位）\n"
                f"2. 短期走势预测（1-2周）\n"
                f"3. 投资建议（买入/持有/卖出及理由）\n"
                f"4. 关键风险提示\n"
                f"请用中文回答，保持专业且简洁。"
            )

            llm_output = await self.run_llm(prompt)

            confidence = 0.0
            if indicators.get("rsi") is not None:
                rsi = indicators["rsi"]
                if 30 < rsi < 70:
                    confidence = 0.75
                elif rsi > 70 or rsi < 30:
                    confidence = 0.6
                else:
                    confidence = 0.5

            return self.make_message(
                agent_name="市场分析师",
                role=AgentRole.MARKET_ANALYST,
                content=llm_output,
                confidence=round(confidence, 2),
                data=indicators,
                thinking=thinking
            )

        except Exception as e:
            logger.exception("市场分析师执行失败")
            return self.make_message(
                agent_name="市场分析师",
                role=AgentRole.MARKET_ANALYST,
                content=f"市场分析师遇到异常: {type(e).__name__}: {str(e)}",
                status=AgentStatus.FAILED,
                data={"error": str(e)}
            )
