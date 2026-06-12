from unittest.mock import AsyncMock, patch

import pytest
from models.schemas import AgentRole, AgentStatus


@pytest.fixture
def mock_llm():
    with patch("agents.base_agent.ChatOpenAI") as MockLLM:
        mock_instance = MockLLM.return_value
        mock_response = type("Response", (), {"content": "AI分析结果"})()
        mock_instance.ainvoke = AsyncMock(return_value=mock_response)
        yield mock_instance


@pytest.mark.asyncio
async def test_market_analyst_analyze(mock_llm):
    from agents.market_analyst import MarketAnalyst

    analyst = MarketAnalyst()

    with patch.object(
        analyst,
        "call_tool",
        new_callable=AsyncMock,
        return_value={
            "current_price": 350.0,
            "change_pct": 1.5,
            "volume": 1000000,
            "ma5": 348.0,
            "ma20": 345.0,
            "ma60": 340.0,
            "macd_dif": 2.5,
            "rsi": 55.0,
            "volatility": 1.2,
            "bb_upper": 360.0,
            "bb_lower": 330.0,
            "high_52w": 400.0,
            "low_52w": 280.0,
        },
    ):
        result = await analyst.analyze("00700")
        assert result.role == AgentRole.MARKET_ANALYST
        assert result.status == AgentStatus.COMPLETED
        assert "traceback" not in result.content.lower()  # No stack trace leak


@pytest.mark.asyncio
async def test_sentiment_scanner_scan(mock_llm):
    from agents.sentiment_scanner import SentimentScanner

    scanner = SentimentScanner()

    with patch.object(scanner, "call_tool", new_callable=AsyncMock) as mock_tool:
        mock_tool.side_effect = [
            {"price": 350.0, "change_pct": 1.5},  # get_stock_price
            {"rsi": 55.0, "volatility": 1.2, "change_pct": 1.5},  # get_technical_indicators
        ]
        result = await scanner.scan("00700")
        assert result.role == AgentRole.SENTIMENT_SCANNER
        assert result.data is not None
        assert "fear_greed_index" in result.data


@pytest.mark.asyncio
async def test_risk_manager_analyze(mock_llm):
    from agents.risk_manager import RiskManager

    manager = RiskManager()

    with patch.object(
        manager,
        "call_tool",
        new_callable=AsyncMock,
        return_value={
            "portfolio_volatility": 18.5,
            "portfolio_var_95": -2.3,
            "risk_level": "中风险",
            "risk_level_num": 55,
            "stock_risks": [
                {"symbol": "00700", "weight": 1.0, "volatility": 18.5, "var_95": -2.3, "max_drawdown": -15.0}
            ],
        },
    ):
        result = await manager.analyze(symbols=[{"symbol": "00700", "weight": 1.0}])
        assert result.role == AgentRole.RISK_MANAGER
        assert result.data is not None
        assert result.data["risk_level"] == 55


@pytest.mark.asyncio
async def test_portfolio_advisor_advise(mock_llm):
    from agents.portfolio_advisor import PortfolioAdvisor

    advisor = PortfolioAdvisor()
    result = await advisor.advise(risk_profile="moderate", investment_amount=100000, symbols=["00700"])
    assert result.role == AgentRole.PORTFOLIO_ADVISOR
    assert result.data is not None
    assert "portfolio_allocation" in result.data
    # Verify allocation sums to ~100%
    total_weight = sum(item["weight"] for item in result.data["portfolio_allocation"])
    assert total_weight == 100


@pytest.mark.asyncio
async def test_agent_error_handling_no_traceback(mock_llm):
    """Verify agents don't leak stack traces in error responses"""
    from agents.market_analyst import MarketAnalyst

    analyst = MarketAnalyst()

    with patch.object(analyst, "call_tool", new_callable=AsyncMock, side_effect=ValueError("test error")):
        result = await analyst.analyze("00700")
        assert result.status == AgentStatus.FAILED
        assert "Traceback" not in result.content
        assert 'File "' not in result.content  # No internal paths
        assert "test error" in result.content  # But error message is preserved
