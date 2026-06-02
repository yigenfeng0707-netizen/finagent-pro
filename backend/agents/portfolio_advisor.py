"""
资产配置Agent - 提供投资组合建议
"""
from .base_agent import BaseAgent
from crewai import Task
from typing import Dict, Any, List
import numpy as np


class PortfolioAdvisor(BaseAgent):
    """资产配置Agent"""
    
    def __init__(self, use_backup: bool = False):
        super().__init__(use_backup)
        self.agent = self.create_agent(
            role="资深资产配置专家",
            goal="根据投资者风险偏好和目标，提供最优资产配置方案",
            backstory="""你是一位拥有CFA证书的资深资产配置专家，曾在全球顶级资管公司工作。
            你精通现代投资组合理论、马科维茨模型、黑-李特曼模型等资产配置方法。
            你善于根据投资者的风险承受能力、投资期限、收益目标，定制个性化投资方案。
            你的建议专业、平衡，既追求收益，又控制风险。"""
        )
    
    def create_portfolio(self, risk_profile: str, investment_amount: float, 
                        investment_horizon: str = "medium") -> Dict[str, Any]:
        """
        创建投资组合
        
        Args:
            risk_profile: 风险偏好 (conservative/moderate/aggressive)
            investment_amount: 投资金额
            investment_horizon: 投资期限 (short/medium/long)
            
        Returns:
            投资组合配置
        """
        # 基于风险偏好的资产配置模板
        allocations = {
            "conservative": {
                "stocks": 30,
                "bonds": 50,
                "cash": 15,
                "gold": 5,
                "expected_return": 5.0,
                "volatility": 8.0,
                "description": "保守型配置，以保本为主，追求稳定收益"
            },
            "moderate": {
                "stocks": 50,
                "bonds": 35,
                "cash": 10,
                "gold": 5,
                "expected_return": 8.0,
                "volatility": 15.0,
                "description": "稳健型配置，平衡收益与风险"
            },
            "aggressive": {
                "stocks": 70,
                "bonds": 20,
                "cash": 5,
                "gold": 5,
                "expected_return": 12.0,
                "volatility": 25.0,
                "description": "进取型配置，追求高收益，承担较高风险"
            }
        }
        
        profile = allocations.get(risk_profile, allocations["moderate"])
        
        # 根据投资期限调整
        if investment_horizon == "long":
            profile["stocks"] += 5
            profile["bonds"] -= 5
            profile["expected_return"] += 1.0
        elif investment_horizon == "short":
            profile["stocks"] -= 5
            profile["cash"] += 5
            profile["expected_return"] -= 1.0
        
        # 计算具体金额
        portfolio = {
            "risk_profile": risk_profile,
            "investment_amount": investment_amount,
            "investment_horizon": investment_horizon,
            "allocation": {
                "stocks": {
                    "percentage": profile["stocks"],
                    "amount": round(investment_amount * profile["stocks"] / 100, 2)
                },
                "bonds": {
                    "percentage": profile["bonds"],
                    "amount": round(investment_amount * profile["bonds"] / 100, 2)
                },
                "cash": {
                    "percentage": profile["cash"],
                    "amount": round(investment_amount * profile["cash"] / 100, 2)
                },
                "gold": {
                    "percentage": profile["gold"],
                    "amount": round(investment_amount * profile["gold"] / 100, 2)
                }
            },
            "expected_return": profile["expected_return"],
            "expected_volatility": profile["volatility"],
            "description": profile["description"]
        }
        
        # 添加具体股票建议（港股示例）
        portfolio["stock_recommendations"] = self._get_stock_recommendations(risk_profile)
        
        return portfolio
    
    def _get_stock_recommendations(self, risk_profile: str) -> List[Dict[str, Any]]:
        """获取股票推荐"""
        recommendations = {
            "conservative": [
                {"symbol": "00005", "name": "汇丰控股", "weight": 20, "reason": "高股息蓝筹股"},
                {"symbol": "00762", "name": "中国联通", "weight": 15, "reason": "稳健电信股"},
                {"symbol": "00883", "name": "中国海洋石油", "weight": 15, "reason": "能源防御股"},
                {"symbol": "02899", "name": "紫金矿业", "weight": 10, "reason": "黄金避险"},
            ],
            "moderate": [
                {"symbol": "00700", "name": "腾讯控股", "weight": 20, "reason": "科技龙头"},
                {"symbol": "03690", "name": "美团", "weight": 15, "reason": "消费互联网"},
                {"symbol": "00005", "name": "汇丰控股", "weight": 15, "reason": "金融蓝筹"},
                {"symbol": "02331", "name": "李宁", "weight": 10, "reason": "消费品牌"},
            ],
            "aggressive": [
                {"symbol": "00700", "name": "腾讯控股", "weight": 25, "reason": "科技龙头"},
                {"symbol": "03690", "name": "美团", "weight": 20, "reason": "高增长互联网"},
                {"symbol": "01810", "name": "小米集团", "weight": 15, "reason": "科技成长"},
                {"symbol": "09618", "name": "京东集团", "weight": 10, "reason": "电商巨头"},
            ]
        }
        return recommendations.get(risk_profile, recommendations["moderate"])
    
    def create_portfolio_task(self, risk_profile: str, investment_amount: float,
                             investment_horizon: str = "medium") -> Task:
        """
        创建资产配置任务
        
        Args:
            risk_profile: 风险偏好
            investment_amount: 投资金额
            investment_horizon: 投资期限
            
        Returns:
            CrewAI Task
        """
        portfolio = self.create_portfolio(risk_profile, investment_amount, investment_horizon)
        
        description = f"""请为以下投资者提供资产配置建议：

投资者画像：
- 风险偏好: {risk_profile}
- 投资金额: {investment_amount}万港币
- 投资期限: {investment_horizon}

基础配置方案：
- 股票: {portfolio['allocation']['stocks']['percentage']}% ({portfolio['allocation']['stocks']['amount']}万)
- 债券: {portfolio['allocation']['bonds']['percentage']}% ({portfolio['allocation']['bonds']['amount']}万)
- 现金: {portfolio['allocation']['cash']['percentage']}% ({portfolio['allocation']['cash']['amount']}万)
- 黄金: {portfolio['allocation']['gold']['percentage']}% ({portfolio['allocation']['gold']['amount']}万)

预期收益: {portfolio['expected_return']}%
预期波动率: {portfolio['expected_volatility']}%

请提供：
1. 配置逻辑说明（为什么选择这个比例）
2. 具体投资标的建议（港股为主）
3. 再平衡策略（何时调整、如何调整）
4. 风险提示和应对
5. 预期收益测算（1年/3年/5年）
"""
        
        return Task(
            description=description,
            agent=self.agent,
            expected_output="详细的资产配置方案，包含配置逻辑、标的建议、再平衡策略和收益测算"
        )
