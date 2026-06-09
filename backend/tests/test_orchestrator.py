import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import AgentOrchestrator
from models.schemas import AgentRole


class TestOrchestrator:
    def test_init(self):
        orch = AgentOrchestrator()
        assert orch.market_analyst is not None
        assert orch.risk_manager is not None
        assert orch.portfolio_advisor is not None
        assert orch.sentiment_scanner is not None

    def test_build_plan(self):
        orch = AgentOrchestrator()
        plan = orch._build_plan(symbols=["00700"], risk_preference="moderate")
        assert plan.total_steps == 4
        assert len(plan.steps) == 4
        assert plan.steps[0].agent_role == AgentRole.MARKET_ANALYST
        assert plan.steps[1].agent_role == AgentRole.SENTIMENT_SCANNER
        assert plan.steps[2].agent_role == AgentRole.RISK_MANAGER
        assert plan.steps[3].agent_role == AgentRole.PORTFOLIO_ADVISOR

    def test_build_plan_dependencies(self):
        orch = AgentOrchestrator()
        plan = orch._build_plan(symbols=["00700"], risk_preference="aggressive")
        assert plan.steps[0].depends_on == []
        assert 1 in plan.steps[1].depends_on
        assert 1 in plan.steps[2].depends_on
        assert 2 in plan.steps[2].depends_on
        assert 1 in plan.steps[3].depends_on
        assert 2 in plan.steps[3].depends_on
        assert 3 in plan.steps[3].depends_on

    def test_synthesize_report_empty(self):
        orch = AgentOrchestrator()
        from models.schemas import AgentContext
        ctx = AgentContext(
            user_input="test",
            symbols=["00700"],
            risk_preference="moderate",
            investment_amount=100000,
            market="hk"
        )
        report = orch.synthesize_report(ctx)
        assert report.recommendation == "hold"
        assert report.confidence == 0.78
