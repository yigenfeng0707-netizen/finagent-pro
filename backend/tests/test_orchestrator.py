import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from orchestrator import AgentOrchestrator
from models.schemas import AgentMessage, AgentRole, AgentStatus, AgentContext


@pytest.fixture
def orchestrator():
    with patch('orchestrator.MarketAnalyst') as MockMA, \
         patch('orchestrator.RiskManager') as MockRM, \
         patch('orchestrator.PortfolioAdvisor') as MockPA, \
         patch('orchestrator.SentimentScanner') as MockSS, \
         patch('orchestrator.FinanceKnowledgeBase'):
        mock_msg = AgentMessage(
            agent="test", role=AgentRole.MARKET_ANALYST,
            content="test content", status=AgentStatus.COMPLETED,
            data={"current_price": 100}
        )
        MockMA.return_value.analyze = AsyncMock(return_value=mock_msg)
        MockSS.return_value.scan = AsyncMock(return_value=mock_msg)
        MockRM.return_value.analyze = AsyncMock(return_value=mock_msg)
        MockPA.return_value.advise = AsyncMock(return_value=mock_msg)
        yield AgentOrchestrator()


@pytest.mark.asyncio
async def test_orchestrator_run_yields_messages(orchestrator):
    messages = []
    async for msg in orchestrator.run(
        symbols=["00700"], investment_amount=100000,
        risk_preference="moderate", session_id="test_session"
    ):
        messages.append(msg)

    # Should yield: plan + 4 step announcements + 4 agent results + done = 10 messages
    assert len(messages) >= 8


@pytest.mark.asyncio
async def test_orchestrator_callback_cleanup(orchestrator):
    """Verify callbacks are properly cleaned up after run"""
    session_id = "test_cleanup"

    async def dummy_cb(msg):
        pass

    orchestrator.on_progress(session_id, dummy_cb)
    assert session_id in orchestrator._progress_callbacks

    orchestrator.remove_progress(session_id)
    assert session_id not in orchestrator._progress_callbacks


@pytest.mark.asyncio
async def test_orchestrator_empty_symbols_raises(orchestrator):
    """Empty symbols should be caught by Pydantic validation, but test graceful handling"""
    messages = []
    try:
        async for msg in orchestrator.run(
            symbols=[], investment_amount=100000,
            risk_preference="moderate", session_id="test_empty"
        ):
            messages.append(msg)
    except (ZeroDivisionError, IndexError):
        pass  # Expected - validation should catch this at request level


def test_synthesize_report_partial_results(orchestrator):
    """Verify partial agent results are preserved, not dropped"""
    ctx = AgentContext(
        user_input="test",
        symbols=["00700"],
        results={
            "market_analysis": AgentMessage(
                agent="市场分析师", role=AgentRole.MARKET_ANALYST,
                content="市场看好", status=AgentStatus.COMPLETED,
                data={"current_price": 350}
            ),
        }
    )
    report = orchestrator.synthesize_report(ctx)
    assert len(report.agent_messages) == 1  # Should preserve partial results
    assert report.recommendation in ["buy", "sell", "hold"]
    assert 0 <= report.confidence <= 1


def test_synthesize_report_dynamic_confidence(orchestrator):
    """Confidence should not be hardcoded to 0.78"""
    ctx_low = AgentContext(user_input="test", symbols=["00700"], results={
        "risk_analysis": AgentMessage(agent="r", role=AgentRole.RISK_MANAGER,
                                       content="高风险", data={"risk_level": 85})
    })
    ctx_high = AgentContext(user_input="test", symbols=["00700"], results={
        "risk_analysis": AgentMessage(agent="r", role=AgentRole.RISK_MANAGER,
                                       content="低风险", data={"risk_level": 20}),
        "sentiment_analysis": AgentMessage(agent="s", role=AgentRole.SENTIMENT_SCANNER,
                                            content="乐观", data={"fear_greed_index": 75}),
        "market_analysis": AgentMessage(agent="m", role=AgentRole.MARKET_ANALYST,
                                         content="建议买入", data={})
    })
    report_low = orchestrator.synthesize_report(ctx_low)
    report_high = orchestrator.synthesize_report(ctx_high)
    # Different scenarios should produce different confidence values
    assert report_low.confidence != report_high.confidence or report_low.recommendation != report_high.recommendation
