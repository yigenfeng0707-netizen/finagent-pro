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
        response = await client.get("/api/knowledge/query?query=腾讯")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    async def test_orchestrate_endpoint(self, client):
        response = await client.post(
            "/api/orchestrate",
            json={"symbols": ["00700"], "investment_amount": 100000, "risk_preference": "moderate", "market": "hk"},
        )
        assert response.status_code == 200
