import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAPI:
    async def test_root(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data

    async def test_health(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert "status" in response.json()

    async def test_stock_analyze_missing_symbol(self, client):
        response = await client.post("/api/stock/analyze", json={"symbol": ""})
        assert response.status_code == 400

    async def test_knowledge_query(self, client):
        import pytest

        pytest.skip("知识库测试需要下载embedding模型，CI环境跳过；本地可手动验证")

    async def test_orchestrate_endpoint(self, client):
        """Mock orchestrator to avoid LLM calls timing out in CI (no API key)."""
        from unittest.mock import patch

        mock_result = {
            "market_analysis": {"content": "模拟市场分析结果", "confidence": 0.85},
            "sentiment_analysis": {"content": "模拟情绪分析", "confidence": 0.80},
            "risk_analysis": {"content": "模拟风险分析", "confidence": 0.90},
            "portfolio_advice": {"content": "模拟投资建议", "confidence": 0.88},
        }

        async def fake_run(*args, **kwargs):
            yield {"type": "agent_message", "data": {"agent": "MarketAnalyst", "content": "OK"}}
            yield {"type": "complete", "data": mock_result}

        with patch("main.orchestrator.run", side_effect=fake_run):
            response = await client.post(
                "/api/orchestrate",
                json={
                    "symbols": ["00700"],
                    "investment_amount": 100000,
                    "risk_preference": "moderate",
                    "market": "hk",
                },
            )
            assert response.status_code == 200
