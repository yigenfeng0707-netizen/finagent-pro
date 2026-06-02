"""
市场分析Agent - 分析市场行情和趋势
"""
from .base_agent import BaseAgent
from crewai import Task
from typing import Dict, Any
import akshare as ak
import pandas as pd


class MarketAnalyst(BaseAgent):
    """市场分析Agent"""
    
    def __init__(self, use_backup: bool = False):
        super().__init__(use_backup)
        self.agent = self.create_agent(
            role="资深市场分析师",
            goal="深入分析港股、美股和A股市场行情，识别趋势和投资机会",
            backstory="""你是一位拥有20年经验的资深市场分析师，精通技术分析和基本面分析。
            你擅长分析股票走势、识别市场趋势、发现投资机会。
            你的分析严谨、数据驱动，能够为投资决策提供有力支持。
            你熟悉港股、美股和A股市场，了解各行业板块的特点。"""
        )
    
    def analyze_stock(self, symbol: str, market: str = "hk") -> Dict[str, Any]:
        """
        分析单只股票
        
        Args:
            symbol: 股票代码
            market: 市场类型 (hk/us/cn)
            
        Returns:
            分析结果字典
        """
        try:
            # 获取股票数据
            if market == "hk":
                df = ak.stock_hk_hist(symbol=symbol, period="daily", start_date="20240101")
            elif market == "us":
                df = ak.stock_us_hist(symbol=symbol, period="daily", start_date="20240101")
            else:  # cn
                df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date="20240101")
            
            if df.empty:
                return {"error": "无法获取股票数据"}
            
            # 计算技术指标
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            # 计算MA
            df['MA5'] = df['收盘'].rolling(window=5).mean()
            df['MA20'] = df['收盘'].rolling(window=20).mean()
            df['MA60'] = df['收盘'].rolling(window=60).mean()
            
            # 计算涨跌幅
            change_pct = (latest['收盘'] - prev['收盘']) / prev['收盘'] * 100
            
            # 计算波动率
            volatility = df['收盘'].pct_change().std() * 100
            
            analysis = {
                "symbol": symbol,
                "market": market,
                "current_price": round(latest['收盘'], 2),
                "change_pct": round(change_pct, 2),
                "volume": int(latest['成交量']),
                "ma5": round(df['MA5'].iloc[-1], 2) if not pd.isna(df['MA5'].iloc[-1]) else None,
                "ma20": round(df['MA20'].iloc[-1], 2) if not pd.isna(df['MA20'].iloc[-1]) else None,
                "ma60": round(df['MA60'].iloc[-1], 2) if not pd.isna(df['MA60'].iloc[-1]) else None,
                "volatility": round(volatility, 2),
                "high_52w": round(df['最高'].max(), 2),
                "low_52w": round(df['最低'].min(), 2),
            }
            
            return analysis
            
        except Exception as e:
            return {"error": f"分析失败: {str(e)}"}
    
    def create_analysis_task(self, symbol: str, market: str = "hk") -> Task:
        """
        创建市场分析任务
        
        Args:
            symbol: 股票代码
            market: 市场类型
            
        Returns:
            CrewAI Task
        """
        # 先获取数据
        data = self.analyze_stock(symbol, market)
        
        if "error" in data:
            description = f"分析股票 {symbol} 失败: {data['error']}"
        else:
            description = f"""请分析 {symbol} 的市场表现：
            
当前价格: {data['current_price']}
涨跌幅: {data['change_pct']}%
成交量: {data['volume']}
5日均线: {data['ma5']}
20日均线: {data['ma20']}
60日均线: {data['ma60']}
波动率: {data['volatility']}%
52周最高: {data['high_52w']}
52周最低: {data['low_52w']}

请提供：
1. 技术面分析（均线排列、趋势判断）
2. 短期走势预测（1-2周）
3. 关键支撑和阻力位
4. 投资建议（买入/持有/卖出）
"""
        
        return Task(
            description=description,
            agent=self.agent,
            expected_output="详细的市场分析报告，包含技术面分析、走势预测、关键价位和投资建议"
        )
