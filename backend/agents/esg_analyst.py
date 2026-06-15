"""ESG分析师Agent — Phase 2 规划

评估上市公司的环境(E)、社会(S)、治理(G)表现，为投资决策提供ESG维度参考。

当前状态: 骨架实现，ESG评级数据接口待接入。
规划数据源: MSCI ESG Ratings / Sustainalytics / 商道融绿ESG评级
"""

from typing import Any, Dict, Optional

from agents.base_agent import BaseAgent
from loguru import logger
from models.schemas import AgentMessage, AgentRole, AgentStatus


class ESGAnalyst(BaseAgent):
    """ESG分析师 — 评估企业ESG表现"""

    def __init__(self):
        super().__init__()
        self.agent = self.create_agent(
            role="ESG分析师",
            goal="评估上市公司的ESG(环境、社会、治理)表现，提供可持续投资建议",
            backstory=(
                "你是一位专业的ESG分析师，擅长评估企业的环境责任、社会责任和公司治理水平。"
                "你关注碳排放、劳工权益、董事会独立性等关键ESG指标，"
                "帮助投资者识别可持续发展风险和机遇。"
            ),
        )

    async def analyze(self, symbol: str, market: str = "hk", context: Optional[Dict] = None) -> AgentMessage:
        """分析企业ESG表现"""
        try:
            # Phase 1: 基于知识库和LLM的ESG分析
            esg_data = self._get_esg_placeholder(symbol, market)

            prompt = f"""请分析 {symbol} 的ESG(环境、社会、治理)表现。

已知信息:
- 股票代码: {symbol}
- 市场: {market}
- 基础ESG数据: {esg_data}

请从以下三个维度进行评估:
1. 环境(E): 碳排放、能源效率、环保合规
2. 社会(S): 劳工权益、社区关系、产品安全
3. 治理(G): 董事会独立性、信息披露、反腐败

给出ESG评级(AAA到CCC)和具体分析。"""

            analysis = await self.run_llm(prompt)

            return self.make_message(
                agent_name="ESG分析师",
                role=AgentRole.MARKET_ANALYST,  # 复用角色，后续可扩展
                content=analysis,
                status=AgentStatus.COMPLETED,
                confidence=0.6,
                data=esg_data,
            )

        except Exception as e:
            logger.error(f"ESG分析失败: {e}")
            return self.make_message(
                agent_name="ESG分析师",
                role=AgentRole.MARKET_ANALYST,
                content=f"ESG分析暂时不可用: {e}",
                status=AgentStatus.FAILED,
            )

    def _get_esg_placeholder(self, symbol: str, market: str) -> Dict[str, Any]:
        """ESG数据占位接口 — Phase 2 接入真实ESG评级数据源

        规划数据源:
        - 商道融绿ESG评级 (国内最权威)
        - MSCI ESG Ratings (国际标准)
        - Sustainalytics (风险导向)
        """
        # 基于行业和市值的粗略ESG评估（占位逻辑）
        sector_esg_map = {
            "00700": {"sector": "互联网", "e_score": 65, "s_score": 70, "g_score": 80},
            "09988": {"sector": "电商/云计算", "e_score": 60, "s_score": 65, "g_score": 75},
            "03690": {"sector": "本地生活", "e_score": 55, "s_score": 70, "g_score": 70},
            "01810": {"sector": "消费电子", "e_score": 50, "s_score": 60, "g_score": 65},
            "00005": {"sector": "银行", "e_score": 45, "s_score": 55, "g_score": 80},
        }

        if symbol in sector_esg_map:
            data = sector_esg_map[symbol]
            avg = (data["e_score"] + data["s_score"] + data["g_score"]) / 3
            data["overall_score"] = round(avg, 1)
            data["rating"] = "AA" if avg >= 75 else "A" if avg >= 65 else "BBB" if avg >= 55 else "BB"
            data["data_source"] = "placeholder (Phase 2: 商道融绿/MSCI)"
            return data

        return {
            "symbol": symbol,
            "overall_score": None,
            "rating": "N/A",
            "data_source": "placeholder (Phase 2: 商道融绿/MSCI)",
            "note": "ESG评级数据待接入，当前为占位数据",
        }
