from typing import Any, Dict, Optional

from loguru import logger
from models.schemas import AgentMessage, AgentRole, AgentStatus
from tools.market_tools import MarketTools

from .base_agent import BaseAgent


class SentimentScanner(BaseAgent):
    def __init__(self, use_backup: bool = False):
        super().__init__(use_backup)
        self.agent = self.create_agent(
            role="市场情绪分析师",
            goal="实时监控和分析市场情绪，识别恐慌和贪婪信号",
            backstory="你是一位经验丰富的市场情绪分析师，擅长从市场数据中捕捉情绪变化。"
            "你能够识别市场的恐慌和贪婪，判断情绪对股价的影响。"
            "你的分析敏锐、及时，能够帮助投资者把握市场情绪转折点。",
        )
        self.register_tool("get_stock_price", MarketTools.get_stock_price)
        self.register_tool("get_technical_indicators", MarketTools.get_technical_indicators)
        self.register_tool("get_fund_flow", MarketTools.get_fund_flow)

    async def scan(self, symbol: str, market: str = "hk", context: Optional[Dict[str, Any]] = None) -> AgentMessage:
        try:
            price_data = await self.call_tool("get_stock_price", symbol=symbol, market=market)
            indicators = await self.call_tool("get_technical_indicators", symbol=symbol, market=market)
            fund_flow = await self.call_tool("get_fund_flow", symbol=symbol, market=market)

            rsi = indicators.get("rsi")
            volatility = indicators.get("volatility", 0)
            change_pct = indicators.get("change_pct", 0)

            # RSI-based sentiment score (0-100)
            rsi_score = 50
            if rsi is not None:
                rsi_score = max(0, min(100, rsi))  # RSI itself as a rough sentiment proxy

            # Fund flow sentiment score
            flow_score = 50
            flow_direction = "无数据"
            if (
                fund_flow
                and not isinstance(fund_flow, dict)
                or (isinstance(fund_flow, dict) and "error" not in fund_flow)
            ):
                net_inflow = fund_flow.get("net_inflow", 0) if isinstance(fund_flow, dict) else 0
                if net_inflow > 0:
                    flow_score = min(80, 50 + abs(net_inflow) / 1e6 * 2)
                    flow_direction = f"净流入 {net_inflow/1e6:.1f}M"
                elif net_inflow < 0:
                    flow_score = max(20, 50 - abs(net_inflow) / 1e6 * 2)
                    flow_direction = f"净流出 {abs(net_inflow)/1e6:.1f}M"
                else:
                    flow_direction = "持平"

            # Price change sentiment
            price_score = max(0, min(100, 50 + change_pct * 5))

            # Multi-dimensional fear & greed index
            data_sources = 1  # at least RSI
            fear_greed = rsi_score * 0.4 + price_score * 0.3 + 50 * 0.3  # default flow weight
            if fund_flow and (not isinstance(fund_flow, dict) or "error" not in fund_flow):
                fear_greed = rsi_score * 0.4 + flow_score * 0.3 + price_score * 0.3
                data_sources += 1
            if change_pct != 0:
                data_sources += 1

            fear_greed = round(max(0, min(100, fear_greed)))

            # Sentiment label
            if fear_greed >= 70:
                sentiment_label = "偏乐观"
            elif fear_greed >= 55:
                sentiment_label = "乐观"
            elif fear_greed >= 45:
                sentiment_label = "中性"
            elif fear_greed >= 30:
                sentiment_label = "偏悲观"
            else:
                sentiment_label = "悲观"

            # Dynamic confidence based on data availability
            confidence = round(0.5 + data_sources * 0.1, 2)

            thinking = (
                f"正在扫描市场情绪...\n"
                f"目标: {symbol}\n"
                f"RSI: {rsi} (评分: {rsi_score:.0f})\n"
                f"资金流向: {flow_direction} (评分: {flow_score:.0f})\n"
                f"涨跌幅: {change_pct}% (评分: {price_score:.0f})\n"
                f"恐惧贪婪指数: {fear_greed}/100 (多源加权)\n"
                f"数据源: {data_sources}个 | 情绪: {sentiment_label}\n"
                "正在综合多维度数据生成情绪分析..."
            )

            fund_flow_text = f"资金流向: {flow_direction}" if flow_direction != "无数据" else "资金流向: 暂无数据"

            prompt = (
                f"你是一位市场情绪分析师。请基于以下多维度数据分析市场情绪。\n\n"
                f"股票代码: {symbol}\n"
                f"当前价格: {price_data.get('price', 'N/A')} HKD\n"
                f"涨跌幅: {change_pct}%\n\n"
                f"技术指标:\n"
                f"  - RSI(14): {rsi}\n"
                f"  - 波动率: {volatility}%\n\n"
                f"资金面数据:\n"
                f"  - {fund_flow_text}\n\n"
                f"综合情绪指标:\n"
                f"  - 恐惧贪婪指数: {fear_greed}/100 (RSI权重40% + 资金流权重30% + 涨跌权重30%)\n"
                f"  - 情绪标签: {sentiment_label}\n\n"
                f"请提供:\n"
                f"1. 市场情绪综合评估（结合技术面和资金面）\n"
                f"2. 情绪对股价的潜在影响\n"
                f"3. 可能的情绪转折点信号\n"
                f"4. 基于情绪的投资建议\n"
                f"请用中文回答，保持专业且简洁。"
            )

            llm_output = await self.run_llm(prompt)

            return self.make_message(
                agent_name="情绪扫描器",
                role=AgentRole.SENTIMENT_SCANNER,
                content=llm_output,
                confidence=confidence,
                data={
                    "fear_greed_index": fear_greed,
                    "fear_greed_label": sentiment_label,
                    "rsi": rsi,
                    "rsi_score": round(rsi_score, 1),
                    "flow_score": round(flow_score, 1),
                    "price_score": round(price_score, 1),
                    "fund_flow_direction": flow_direction,
                    "volatility": volatility,
                    "change_pct": change_pct,
                    "data_sources": data_sources,
                },
                thinking=thinking,
            )

        except Exception as e:
            logger.exception("情绪扫描器执行失败")
            return self.make_message(
                agent_name="情绪扫描器",
                role=AgentRole.SENTIMENT_SCANNER,
                content=f"情绪扫描器遇到异常: {type(e).__name__}: {str(e)}",
                status=AgentStatus.FAILED,
                data={"error": str(e)},
            )
