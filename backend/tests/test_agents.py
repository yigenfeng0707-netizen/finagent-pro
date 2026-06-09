import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.market_analyst import MarketAnalyst
from agents.risk_manager import RiskManager
from agents.portfolio_advisor import PortfolioAdvisor
from agents.sentiment_scanner import SentimentScanner
from models.schemas import AgentRole, AgentStatus


class TestMarketAnalyst:
    def test_init(self):
        agent = MarketAnalyst()
        assert agent.agent is not None
        assert agent._tools is not None

    def test_tool_registration(self):
        agent = MarketAnalyst()
        assert "get_stock_price" in agent._tools
        assert "get_technical_indicators" in agent._tools


class TestRiskManager:
    def test_init(self):
        agent = RiskManager()
        assert agent.agent is not None
        assert "get_portfolio_risk" in agent._tools

    def test_calculate_var(self):
        agent = RiskManager()
        result = agent.call_tool("calculate_var", returns=[-0.01, 0.02, -0.005, 0.015])
        assert result <= 0


class TestPortfolioAdvisor:
    def test_init(self):
        agent = PortfolioAdvisor()
        assert agent.agent is not None

    def test_make_message(self):
        agent = PortfolioAdvisor()
        msg = agent.make_message("测试", AgentRole.PORTFOLIO_ADVISOR, "test")
        assert msg.agent == "测试"
        assert msg.role == AgentRole.PORTFOLIO_ADVISOR
        assert msg.content == "test"


class TestSentimentScanner:
    def test_init(self):
        agent = SentimentScanner()
        assert agent.agent is not None
        assert "get_stock_price" in agent._tools
