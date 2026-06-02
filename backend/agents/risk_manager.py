"""
风险管理Agent - 评估投资风险
"""
from .base_agent import BaseAgent
from crewai import Task
from typing import Dict, Any, List
import numpy as np
import akshare as ak


class RiskManager(BaseAgent):
    """风险管理Agent"""
    
    def __init__(self, use_backup: bool = False):
        super().__init__(use_backup)
        self.agent = self.create_agent(
            role="首席风险官",
            goal="全面评估投资组合风险，提供风险预警和管理建议",
            backstory="""你是一位拥有CFA和FRM双证的首席风险官，在顶级投行工作15年。
            你精通VaR模型、压力测试、情景分析等风险管理工具。
            你善于识别市场风险、信用风险、流动性风险等各类风险。
            你的风险评估严谨、全面，能够帮助投资者规避重大损失。"""
        )
    
    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """
        计算VaR（风险价值）
        
        Args:
            returns: 收益率序列
            confidence: 置信水平
            
        Returns:
            VaR值
        """
        if not returns:
            return 0.0
        return np.percentile(returns, (1 - confidence) * 100)
    
    def analyze_portfolio_risk(self, symbols: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析投资组合风险
        
        Args:
            symbols: 股票列表，每项包含symbol、market、weight
            
        Returns:
            风险分析结果
        """
        try:
            portfolio_returns = []
            stock_risks = []
            
            for item in symbols:
                symbol = item['symbol']
                market = item.get('market', 'hk')
                weight = item.get('weight', 1.0 / len(symbols))
                
                # 获取历史数据
                if market == "hk":
                    df = ak.stock_hk_hist(symbol=symbol, period="daily", start_date="20240101")
                elif market == "us":
                    df = ak.stock_us_hist(symbol=symbol, period="daily", start_date="20240101")
                else:
                    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date="20240101")
                
                if df.empty:
                    continue
                
                # 计算收益率
                df['return'] = df['收盘'].pct_change()
                returns = df['return'].dropna().tolist()
                
                if returns:
                    # 计算个股风险指标
                    volatility = np.std(returns) * np.sqrt(252) * 100  # 年化波动率
                    var_95 = self.calculate_var(returns, 0.95) * 100
                    max_drawdown = ((df['收盘'] / df['收盘'].cummax()) - 1).min() * 100
                    
                    stock_risks.append({
                        "symbol": symbol,
                        "weight": weight,
                        "volatility": round(volatility, 2),
                        "var_95": round(var_95, 2),
                        "max_drawdown": round(max_drawdown, 2)
                    })
                    
                    # 加权组合收益率
                    weighted_returns = [r * weight for r in returns]
                    portfolio_returns.extend(weighted_returns)
            
            if not portfolio_returns:
                return {"error": "无法计算组合风险"}
            
            # 计算组合风险指标
            portfolio_volatility = np.std(portfolio_returns) * np.sqrt(252) * 100
            portfolio_var_95 = self.calculate_var(portfolio_returns, 0.95) * 100
            
            # 风险评级
            if portfolio_volatility < 15:
                risk_level = "低风险"
            elif portfolio_volatility < 25:
                risk_level = "中风险"
            else:
                risk_level = "高风险"
            
            return {
                "portfolio_volatility": round(portfolio_volatility, 2),
                "portfolio_var_95": round(portfolio_var_95, 2),
                "risk_level": risk_level,
                "stock_risks": stock_risks,
                "recommendation": self._get_risk_recommendation(portfolio_volatility, portfolio_var_95)
            }
            
        except Exception as e:
            return {"error": f"风险分析失败: {str(e)}"}
    
    def _get_risk_recommendation(self, volatility: float, var_95: float) -> str:
        """获取风险建议"""
        if volatility < 15 and var_95 > -2:
            return "组合风险较低，适合稳健型投资者。可适当增加权益类资产配置。"
        elif volatility < 25 and var_95 > -4:
            return "组合风险适中，注意分散投资。建议定期再平衡。"
        else:
            return "组合风险较高，建议增加防御性资产（债券、黄金）配置，降低单一股票集中度。"
    
    def create_risk_task(self, portfolio: List[Dict[str, Any]]) -> Task:
        """
        创建风险评估任务
        
        Args:
            portfolio: 投资组合
            
        Returns:
            CrewAI Task
        """
        risk_data = self.analyze_portfolio_risk(portfolio)
        
        if "error" in risk_data:
            description = f"风险评估失败: {risk_data['error']}"
        else:
            description = f"""请评估以下投资组合的风险：

组合波动率: {risk_data['portfolio_volatility']}%
VaR(95%): {risk_data['portfolio_var_95']}%
风险等级: {risk_data['risk_level']}

个股风险详情:
"""
            for stock in risk_data['stock_risks']:
                description += f"- {stock['symbol']}: 权重{stock['weight']*100}%, 波动率{stock['volatility']}%, VaR{stock['var_95']}%\n"
            
            description += f"""
请提供：
1. 组合风险分析（波动率、VaR解读）
2. 个股风险贡献度分析
3. 风险预警（如有高风险股票）
4. 风险管理建议（如何降低风险）
5. 适合的投资者类型
"""
        
        return Task(
            description=description,
            agent=self.agent,
            expected_output="详细的风险评估报告，包含风险分析、预警和建议"
        )
