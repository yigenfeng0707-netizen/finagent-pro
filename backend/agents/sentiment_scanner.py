"""
情绪分析Agent - 分析市场情绪
"""
from .base_agent import BaseAgent
from crewai import Task
from typing import Dict, Any, List
import os
import requests
from datetime import datetime, timedelta


class SentimentScanner(BaseAgent):
    """情绪分析Agent"""
    
    def __init__(self, use_backup: bool = False):
        super().__init__(use_backup)
        self.agent = self.create_agent(
            role="市场情绪分析师",
            goal="实时监控和分析市场情绪，识别恐慌和贪婪信号",
            backstory="""你是一位经验丰富的市场情绪分析师，擅长从新闻、社交媒体、市场数据中捕捉情绪变化。
            你能够识别市场的恐慌和贪婪，判断情绪对股价的影响。
            你的分析敏锐、及时，能够帮助投资者把握市场情绪转折点。"""
        )
        self.finnhub_key = os.getenv("FINNHUB_API_KEY")
    
    def get_news_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        获取新闻情绪
        
        Args:
            symbol: 股票代码
            
        Returns:
            情绪分析结果
        """
        try:
            # 使用Finnhub获取新闻
            if self.finnhub_key:
                url = f"https://finnhub.io/api/v1/company-news"
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                
                params = {
                    "symbol": symbol,
                    "from": start_date.strftime("%Y-%m-%d"),
                    "to": end_date.strftime("%Y-%m-%d"),
                    "token": self.finnhub_key
                }
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    news = response.json()
                    
                    # 简单情绪分析（基于关键词）
                    positive_words = ['上涨', '增长', '利好', '突破', '强劲', '超预期', '买入', '增持']
                    negative_words = ['下跌', '下滑', '利空', '跌破', '疲软', '不及预期', '卖出', '减持']
                    
                    sentiment_scores = []
                    for item in news[:10]:  # 分析最近10条
                        headline = item.get('headline', '') + ' ' + item.get('summary', '')
                        score = 0
                        for word in positive_words:
                            if word in headline:
                                score += 1
                        for word in negative_words:
                            if word in headline:
                                score -= 1
                        sentiment_scores.append(score)
                    
                    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
                    
                    if avg_sentiment > 0.5:
                        sentiment = "积极"
                    elif avg_sentiment < -0.5:
                        sentiment = "消极"
                    else:
                        sentiment = "中性"
                    
                    return {
                        "symbol": symbol,
                        "sentiment": sentiment,
                        "score": round(avg_sentiment, 2),
                        "news_count": len(news),
                        "recent_headlines": [n.get('headline', '') for n in news[:5]]
                    }
            
            # 如果没有Finnhub或请求失败，返回模拟数据
            return {
                "symbol": symbol,
                "sentiment": "中性",
                "score": 0,
                "news_count": 0,
                "recent_headlines": [],
                "note": "新闻数据暂不可用"
            }
            
        except Exception as e:
            return {
                "symbol": symbol,
                "sentiment": "未知",
                "score": 0,
                "error": str(e)
            }
    
    def get_market_sentiment(self) -> Dict[str, Any]:
        """
        获取整体市场情绪
        
        Returns:
            市场情绪指标
        """
        # 模拟市场情绪指标
        indicators = {
            "fear_greed_index": 65,  # 0-100，50为中性
            "fear_greed_label": "贪婪",  # 极度恐慌/恐慌/中性/贪婪/极度贪婪
            "vix_level": "normal",  # low/normal/high
            "market_breadth": "positive",  # positive/neutral/negative
            "put_call_ratio": 0.85,  # 低于1为看涨
        }
        
        return indicators
    
    def create_sentiment_task(self, symbol: str) -> Task:
        """
        创建情绪分析任务
        
        Args:
            symbol: 股票代码
            
        Returns:
            CrewAI Task
        """
        sentiment_data = self.get_news_sentiment(symbol)
        market_sentiment = self.get_market_sentiment()
        
        description = f"""请分析 {symbol} 的市场情绪：

个股情绪指标：
- 情绪评分: {sentiment_data.get('score', 0)}
- 情绪标签: {sentiment_data.get('sentiment', '未知')}
- 相关新闻数: {sentiment_data.get('news_count', 0)}

市场整体情绪：
- 恐惧贪婪指数: {market_sentiment['fear_greed_index']} ({market_sentiment['fear_greed_label']})
- VIX水平: {market_sentiment['vix_level']}
- 市场广度: {market_sentiment['market_breadth']}
-  put/call比率: {market_sentiment['put_call_ratio']}

近期新闻标题：
"""
        for headline in sentiment_data.get('recent_headlines', [])[:3]:
            description += f"- {headline}\n"
        
        description += """
请提供：
1. 情绪分析（个股+市场整体）
2. 情绪对股价的潜在影响
3. 情绪转折点识别
4. 投资建议（基于情绪）
"""
        
        return Task(
            description=description,
            agent=self.agent,
            expected_output="详细的市场情绪分析报告"
        )
