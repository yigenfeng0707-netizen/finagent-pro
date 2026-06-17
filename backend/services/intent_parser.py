"""意图识别模块 — 使用 LLM 解析用户自然语言请求"""

import json
import re
from typing import Any, Dict, Optional

from loguru import logger

# 港股代码映射（用于回退和验证）
HK_STOCK_ALIASES: Dict[str, str] = {
    "腾讯": "00700",
    "腾讯控股": "00700",
    "tencent": "00700",
    "阿里": "09988",
    "阿里巴巴": "09988",
    "alibaba": "09988",
    "美团": "03690",
    "meituan": "03690",
    "小米": "01810",
    "小米集团": "01810",
    "xiaomi": "01810",
    "友邦": "01299",
    "友邦保险": "01299",
    "平安": "02318",
    "中国平安": "02318",
    "中海油": "00883",
    "中国海洋石油": "00883",
    "中国移动": "00941",
    "汇丰": "00005",
    "汇丰控股": "00005",
    "hsbc": "00005",
    "京东": "09618",
    "京东集团": "09618",
    "jd": "09618",
    "李宁": "02331",
    "紫金矿业": "02899",
    "中国联通": "00762",
}

RISK_ALIASES = {
    "保守": "conservative",
    "稳健": "moderate",
    "进取": "aggressive",
    "激进": "aggressive",
}

# 港股代码格式正则
HK_CODE_PATTERN = re.compile(r"\b(\d{5})\b")


def _extract_symbols_fast(text: str) -> list[str]:
    """快速规则提取股票代码（无需 LLM 调用）"""
    symbols = []
    text_lower = text.lower()

    # 匹配港股代码格式
    code_matches = HK_CODE_PATTERN.findall(text)
    for code in code_matches:
        if code not in symbols:
            symbols.append(code)

    # 匹配中文/英文别名
    for alias, code in HK_STOCK_ALIASES.items():
        if alias.lower() in text_lower and code not in symbols:
            symbols.append(code)

    return symbols


def _extract_risk_fast(text: str) -> Optional[str]:
    """快速规则提取风险偏好"""
    for alias, risk in RISK_ALIASES.items():
        if alias in text:
            return risk
    return None


def _extract_amount_fast(text: str) -> Optional[float]:
    """快速规则提取投资金额"""
    # 匹配 "10万" "100000" "10w" 等格式
    patterns = [
        r"(\d+(?:\.\d+)?)\s*万",  # 10万
        r"(\d+(?:\.\d+)?)\s*w\b",  # 10w
        r"(\d{5,})\s*(?:港币|hk|HKD|hkd)?",  # 100000
        r"投资.*?(\d+(?:\.\d+)?)\s*万",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            val = float(match.group(1))
            if "万" in pattern or "w" in pattern.lower():
                val *= 10000
            return val
    return None


async def parse_intent_with_llm(text: str, run_llm_func) -> Dict[str, Any]:
    """使用 LLM 解析用户意图（当规则匹配不足时调用）"""
    prompt = f"""你是一个金融投资助手的意图识别模块。请分析用户消息，提取以下信息并以JSON格式返回：

用户消息: "{text}"

请返回JSON（不要包含其他文字）:
{{
  "intent": "analyze|chat|question",
  "symbols": ["股票代码列表，港股5位数字如00700"],
  "risk_preference": "conservative|moderate|aggressive|null",
  "investment_amount": 金额数字或null,
  "market": "hk|us|cn",
  "query_type": "stock_analysis|portfolio|risk|market_overview|general"
}}

注意：
- intent为analyze表示用户想分析股票，chat表示闲聊，question表示提问
- symbols必须是5位港股代码（如00700不是7700）
- 如果用户提到"腾讯"对应00700，"阿里"对应09988，"美团"对应03690，"小米"对应01810
- 如果无法确定具体股票，symbols返回空数组
- risk_preference如果用户没提到则为null"""

    try:
        response = await run_llm_func(prompt)
        # 提取JSON
        json_match = re.search(r"\{[^}]+\}", response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result
    except Exception as e:
        logger.warning(f"LLM 意图解析失败: {e}")

    return {
        "intent": "chat",
        "symbols": [],
        "risk_preference": None,
        "investment_amount": None,
        "market": "hk",
        "query_type": "general",
    }


async def parse_user_intent(text: str, run_llm_func=None) -> Dict[str, Any]:
    """解析用户意图 — 先用规则快速匹配，不足时回退到 LLM"""
    symbols = _extract_symbols_fast(text)
    risk = _extract_risk_fast(text)
    amount = _extract_amount_fast(text)

    # 规则匹配成功，直接返回
    if symbols:
        intent = "analyze"
        query_type = "stock_analysis"
    elif any(w in text for w in ["分析", "看看", "怎么样", "评估", "建议", "买入", "卖出"]):
        intent = "analyze"
        query_type = "stock_analysis"
    elif any(w in text for w in ["组合", "配置", "资产"]):
        intent = "analyze"
        query_type = "portfolio"
    elif any(w in text for w in ["风险", "止损"]):
        intent = "analyze"
        query_type = "risk"
    else:
        intent = "chat"
        query_type = "general"

    # 如果规则匹配不足且有 LLM 可用，使用 LLM 增强
    if not symbols and run_llm_func is not None:
        llm_result = await parse_intent_with_llm(text, run_llm_func)
        if llm_result.get("symbols"):
            symbols = llm_result["symbols"]
            intent = llm_result.get("intent", intent)
            query_type = llm_result.get("query_type", query_type)
        if not risk and llm_result.get("risk_preference"):
            risk = llm_result["risk_preference"]
        if not amount and llm_result.get("investment_amount"):
            amount = llm_result["investment_amount"]

    return {
        "intent": intent,
        "symbols": symbols,
        "risk_preference": risk or "moderate",
        "investment_amount": amount or 100000,
        "market": "hk",
        "query_type": query_type,
    }
