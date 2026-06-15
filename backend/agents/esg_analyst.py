"""ESG分析师Agent — 基于真实ESG评级数据

评估上市公司的环境(E)、社会(S)、治理(G)表现，为投资决策提供ESG维度参考。

数据源:
- MSCI ESG Ratings (国际标准，712只港股覆盖)
- 商道融绿ESG评级 (国内最权威，8200+条数据)
- 华证ESG评级 (A股+港股，6250+条数据)

数据通过AKShare免费接口获取（底层为东方财富/新浪财经公开API）。
"""

import asyncio
from typing import Any, Dict, Optional

import akshare as ak
import pandas as pd
from agents.base_agent import BaseAgent
from loguru import logger
from models.schemas import AgentMessage, AgentRole, AgentStatus


class ESGAnalyst(BaseAgent):
    """ESG分析师 — 基于真实ESG评级数据评估企业ESG表现"""

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
        # 缓存ESG数据，避免重复API调用
        self._msci_cache: Optional[pd.DataFrame] = None
        self._zd_cache: Optional[pd.DataFrame] = None
        self._hz_cache: Optional[pd.DataFrame] = None

    def _get_msci_data(self, symbol: str, market: str = "hk") -> Optional[Dict[str, Any]]:
        """获取MSCI ESG评级数据"""
        try:
            if self._msci_cache is None:
                self._msci_cache = ak.stock_esg_msci_sina()
            code = f"{symbol}.HK" if market == "hk" else symbol
            row = self._msci_cache[self._msci_cache["股票代码"] == code]
            if row.empty:
                return None
            r = row.iloc[0]
            return {
                "rating": r.get("ESG评分", "N/A"),
                "environment_score": float(r.get("环境总评", 0)),
                "social_score": float(r.get("社会责任总评", 0)),
                "governance_score": float(r.get("治理总评", 0)),
                "date": str(r.get("评级日期", "")),
                "source": "MSCI ESG Ratings",
            }
        except Exception as e:
            logger.warning(f"MSCI ESG数据获取失败({symbol}): {e}")
            return None

    def _get_zd_data(self, symbol: str, market: str = "hk") -> Optional[Dict[str, Any]]:
        """获取商道融绿ESG评级数据"""
        try:
            if self._zd_cache is None:
                self._zd_cache = ak.stock_esg_zd_sina()
            code = f"{symbol}.HK" if market == "hk" else symbol
            row = self._zd_cache[self._zd_cache["股票代码"] == code]
            if row.empty:
                return None
            r = row.iloc[0]
            # 解析 "71.95(AA)" 格式
            def parse_score(val):
                try:
                    return float(str(val).split("(")[0])
                except (ValueError, IndexError):
                    return 0.0
            def parse_grade(val):
                try:
                    return str(val).split("(")[1].rstrip(")")
                except (IndexError):
                    return str(val)
            esg_val = r.get("ESG评分", "")
            return {
                "overall_score": parse_score(esg_val),
                "overall_grade": parse_grade(esg_val),
                "environment_score": parse_score(r.get("环境总评", "")),
                "environment_grade": parse_grade(r.get("环境总评", "")),
                "social_score": parse_score(r.get("社会责任总评", "")),
                "social_grade": parse_grade(r.get("社会责任总评", "")),
                "governance_score": parse_score(r.get("治理总评", "")),
                "governance_grade": parse_grade(r.get("治理总评", "")),
                "date": str(r.get("评分日期", "")),
                "source": "商道融绿ESG评级",
            }
        except Exception as e:
            logger.warning(f"商道融绿ESG数据获取失败({symbol}): {e}")
            return None

    def _get_hz_data(self, symbol: str, market: str = "hk") -> Optional[Dict[str, Any]]:
        """获取华证ESG评级数据"""
        try:
            if self._hz_cache is None:
                self._hz_cache = ak.stock_esg_hz_sina()
            code = f"{symbol}.HK" if market == "hk" else symbol
            row = self._hz_cache[self._hz_cache["股票代码"] == code]
            if row.empty:
                return None
            r = row.iloc[0]
            return {
                "overall_score": float(r.get("ESG评分", 0)),
                "overall_grade": str(r.get("ESG等级", "")),
                "environment_score": float(r.get("环境", 0)),
                "environment_grade": str(r.get("环境等级", "")),
                "social_score": float(r.get("社会", 0)),
                "social_grade": str(r.get("社会等级", "")),
                "governance_score": float(r.get("公司治理", 0)),
                "governance_grade": str(r.get("公司治理等级", "")),
                "name": str(r.get("股票名称", "")),
                "date": str(r.get("日期", "")),
                "source": "华证ESG评级",
            }
        except Exception as e:
            logger.warning(f"华证ESG数据获取失败({symbol}): {e}")
            return None

    def get_esg_data(self, symbol: str, market: str = "hk") -> Dict[str, Any]:
        """聚合三家ESG评级数据"""
        result = {"symbol": symbol, "market": market, "sources": {}}

        msci = self._get_msci_data(symbol, market)
        if msci:
            result["sources"]["msci"] = msci

        zd = self._get_zd_data(symbol, market)
        if zd:
            result["sources"]["shangdao_ronglv"] = zd

        hz = self._get_hz_data(symbol, market)
        if hz:
            result["sources"]["huazheng"] = hz

        # 综合评级（优先商道融绿，其次华证，最后MSCI）
        if zd:
            result["overall_rating"] = zd["overall_grade"]
            result["overall_score"] = zd["overall_score"]
        elif hz:
            result["overall_rating"] = hz["overall_grade"]
            result["overall_score"] = hz["overall_score"]
        elif msci:
            result["overall_rating"] = msci["rating"]
            result["overall_score"] = None
        else:
            result["overall_rating"] = "N/A"
            result["overall_score"] = None

        result["data_sources_count"] = len(result["sources"])
        return result

    async def analyze(self, symbol: str, market: str = "hk", context: Optional[Dict] = None) -> AgentMessage:
        """分析企业ESG表现"""
        try:
            # 获取真实ESG评级数据
            esg_data = await asyncio.to_thread(self.get_esg_data, symbol, market)

            # 构建ESG分析Prompt
            sources_info = []
            for src_name, src_data in esg_data.get("sources", {}).items():
                sources_info.append(f"- {src_data.get('source', src_name)}: {src_data}")

            sources_text = "\n".join(sources_info) if sources_info else "暂无ESG评级数据"

            prompt = f"""请分析 {symbol} 的ESG(环境、社会、治理)表现。

真实ESG评级数据:
{sources_text}

请基于以上真实评级数据，从以下三个维度进行深度评估:
1. 环境(E): 碳排放、能源效率、环保合规、绿色转型进展
2. 社会(S): 劳工权益、社区关系、产品安全、数据隐私
3. 治理(G): 董事会独立性、信息披露、反腐败、股东权益

给出:
- 综合ESG评级判断
- 各维度优劣势分析
- ESG风险提示
- 可持续投资建议"""

            analysis = await self.run_llm(prompt)

            return self.make_message(
                agent_name="ESG分析师",
                role=AgentRole.MARKET_ANALYST,
                content=analysis,
                status=AgentStatus.COMPLETED,
                confidence=0.8 if esg_data["data_sources_count"] > 0 else 0.4,
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
